"""
LLM Service — Gemma 4 E2B via Ollama
Handles streaming chat inference with persona system prompt.
"""
import ollama
import asyncio
import re
from config import OLLAMA_MODEL, SYSTEM_PROMPT, OLLAMA_HOST


class LLMService:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.client = ollama.AsyncClient(host=OLLAMA_HOST)
        self.conversation_history = []
        self._init_conversation()

    def _init_conversation(self):
        """Initialize conversation with system prompt persona."""
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def reset_conversation(self):
        """Reset conversation history, keeping system prompt."""
        self._init_conversation()

    async def chat_stream(self, user_message: str):
        """
        Stream chat response from Gemma 4.
        Yields dict with 'token' and optionally 'expression'.
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        full_response = ""

        try:
            stream = await self.client.chat(
                model=self.model,
                messages=self.conversation_history,
                stream=True,
            )

            async for chunk in stream:
                token = chunk["message"]["content"]
                full_response += token

                # Check if we have a complete expression tag
                expression = None
                expr_match = re.search(
                    r'\[EXPRESSION:(\w+)\]', full_response
                )
                if expr_match:
                    expression = expr_match.group(1)

                yield {
                    "token": token,
                    "expression": expression,
                    "done": False,
                }

            # Clean expression tag from final response
            clean_response = re.sub(
                r'\s*\[EXPRESSION:\w+\]\s*', '', full_response
            ).strip()

            # Extract final expression
            final_expression = "neutral"
            expr_match = re.search(
                r'\[EXPRESSION:(\w+)\]', full_response
            )
            if expr_match:
                final_expression = expr_match.group(1)

            # Save cleaned response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": clean_response
            })

            # Keep conversation history manageable (last 20 exchanges)
            if len(self.conversation_history) > 41:  # 1 system + 20 pairs
                self.conversation_history = (
                    [self.conversation_history[0]]
                    + self.conversation_history[-40:]
                )

            yield {
                "token": "",
                "expression": final_expression,
                "done": True,
                "full_response": clean_response,
            }

        except Exception as e:
            yield {
                "token": f"[Error: {str(e)}]",
                "expression": "sad",
                "done": True,
                "error": str(e),
            }

    async def check_connection(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            models = await self.client.list()
            model_names = [m.model for m in models.models]
            return any(self.model in name for name in model_names)
        except Exception:
            return False

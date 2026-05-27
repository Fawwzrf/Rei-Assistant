"""
LLM Service — Gemma 3 via Ollama (LangChain Version with Web Search & Memory Summarization)
Handles streaming chat inference, DuckDuckGo search integration, and history summarization.
"""
import ollama
import asyncio
import re
from typing import AsyncGenerator
# pyrefly: ignore [missing-import]
from langchain_ollama import ChatOllama
# pyrefly: ignore [missing-import]
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
# pyrefly: ignore [missing-import]
from langchain_community.tools import DuckDuckGoSearchRun
from config import OLLAMA_MODEL, SYSTEM_PROMPT, OLLAMA_HOST, OLLAMA_OPTIONS
from services.memory_service import MemoryService


class LLMService:
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.client = ollama.AsyncClient(host=OLLAMA_HOST)
        self.memory = MemoryService()
        
        # Inisialisasi ChatOllama dari LangChain
        self.llm = ChatOllama(
            model=self.model,
            base_url=OLLAMA_HOST,
            temperature=OLLAMA_OPTIONS.get("temperature", 0.7),
            num_ctx=OLLAMA_OPTIONS.get("num_ctx", 4096),
            top_p=OLLAMA_OPTIONS.get("top_p", 0.9),
        )
        
        # Inisialisasi DuckDuckGo Search Tool
        self.search_tool = DuckDuckGoSearchRun()
        # Bind tool ke LLM untuk mendukung native tool calling
        self.llm_with_tools = self.llm.bind_tools([self.search_tool])
        self.supports_tools = True
        
        self.conversation_history = []
        self._init_conversation()

    def _init_conversation(self):
        """Initialize conversation with system prompt persona using LangChain Messages."""
        self.conversation_history = [
            SystemMessage(content=SYSTEM_PROMPT)
        ]

    def reset_conversation(self):
        """Reset conversation history, keeping system prompt."""
        self._init_conversation()

    async def _summarize_history(self):
        """
        Summarize older conversation history to save context tokens.
        Keeps the System Prompt, the running summary, and the most recent messages.
        """
        
    
        start_idx = 1
        has_existing_summary = False
        if len(self.conversation_history) > 1 and isinstance(self.conversation_history[1], SystemMessage) and self.conversation_history[1].content.startswith("Rangkuman percakapan sebelumnya:"):
            start_idx = 2
            has_existing_summary = True

        chat_messages = self.conversation_history[start_idx:]
        
        # Jika chat messages melebihi 10 pesan (artinya 5 putaran tanya-jawab)
        if len(chat_messages) > 10:
            print("[LLMService] Memulai perangkuman riwayat percakapan lama...")
            # Ambil 6 pesan tertua untuk dirangkum
            messages_to_summarize = chat_messages[:6]
            messages_to_keep = chat_messages[6:]
            
            # Format pesan menjadi teks untuk dikirim ke LLM
            formatted_text = ""
            for msg in messages_to_summarize:
                role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                formatted_text += f"{role}: {msg.content}\n"
                
            existing_summary_prompt = ""
            if has_existing_summary:
                existing_summary_prompt = f"Rangkuman sebelumnya:\n{self.conversation_history[1].content}\n\n"

            summary_prompt = (
                f"Tugas Anda adalah merangkum percakapan berikut secara sangat singkat dan padat dalam 1-2 kalimat Bahasa Indonesia.\n\n"
                f"{existing_summary_prompt}"
                f"Percakapan baru untuk dirangkum:\n{formatted_text}\n"
                f"Rangkuman terpadu:"
            )
            
            try:
                # Panggil LLM secara langsung tanpa tools untuk perangkuman cepat
                response = await self.llm.ainvoke([HumanMessage(content=summary_prompt)])
                summary_text = response.content.strip()
                
                # Buat SystemMessage rangkuman baru
                summary_msg = SystemMessage(content=f"Rangkuman percakapan sebelumnya: {summary_text}")
                
                # Susun ulang riwayat percakapan
                self.conversation_history = [self.conversation_history[0], summary_msg] + messages_to_keep
                print(f"[LLMService] Riwayat berhasil dirangkum: {summary_text}")
            except Exception as e:
                print(f"[LLMService] Gagal merangkum riwayat: {e}")

    async def chat_stream(self, user_message: str) -> AsyncGenerator[dict, None]:
        """
        Stream chat response from Gemma 3, supporting Web Search and Memory Summarization.
        Yields dict with 'token' and optionally 'expression'.
        """
        # Tambahkan pesan pengguna ke riwayat
        msg_payload = HumanMessage(content=user_message)
        self.conversation_history.append(msg_payload)

        # --- PRE-EMPTIVE WEB SEARCH ROUTING (FALLBACK) ---
        # Mencari tahu apakah query membutuhkan info real-time secara preemptive
        needs_search = False
        search_keywords = ["cuaca", "suhu", "berita", "presiden", "juara", "kurs", "hari ini", "ddg:", "search", "cari di internet"]
        if any(kw in user_message.lower() for kw in search_keywords):
            needs_search = True

        search_context = ""
        if needs_search:
            # Bersihkan query pencarian
            search_query = re.sub(r'(ddg:|search|cari di internet)', '', user_message, flags=re.IGNORECASE).strip()
            if not search_query:
                search_query = user_message
            try:
                print(f"[LLMService] Pre-emptive search trigger untuk query: '{search_query}'")
                loop = asyncio.get_event_loop()
                search_context = await loop.run_in_executor(None, self.search_tool.run, search_query)
                print(f"[LLMService] Hasil search didapatkan ({len(search_context)} karakter)")
            except Exception as e:
                print(f"[LLMService] Pre-emptive search error: {e}")

        # Jalankan RAG lokal (MemoryService)
        context_str = ""
        if len(user_message.split()) > 3:
            loop = asyncio.get_event_loop()
            context_str = await loop.run_in_executor(
                None, self.memory.query_context, user_message
            )

        messages_to_send = list(self.conversation_history)
        
        # Gabungkan hasil pencarian internet dan konteks RAG lokal jika ada
        augmented_prompt = user_message
        context_blocks = []
        if search_context:
            context_blocks.append(f"[INFO SISTEM - HASIL PENCARIAN INTERNET REAL-TIME:\n{search_context}]")
        if context_str:
            context_blocks.append(f"[INFO SISTEM - KONTEKS LOKAL/INGATAN:\n{context_str}]")
            
        if context_blocks:
            context_joined = "\n\n".join(context_blocks)
            augmented_prompt = (
                f"{user_message}\n\n"
                f"{context_joined}\n\n"
                f"Catatan: Jawablah pertanyaan pengguna menggunakan konteks sistem di atas jika relevan saja. Jangan sebutkan bahwa Anda mencari di internet atau membaca database ingatan sistem."
            )
            messages_to_send[-1] = HumanMessage(content=augmented_prompt)

        full_response = ""

        try:
            # Jika pencarian preemptive sudah dilakukan, kita tidak perlu memicu tool calling model
            use_fallback = False
            tool_calls = []
            
            if search_context or not self.supports_tools:
                stream = self.llm.astream(messages_to_send)
            else:
                # Gunakan model yang di-bind dengan tools
                stream = self.llm_with_tools.astream(messages_to_send)

            try:
                async for chunk in stream:
                    # Periksa apakah model ingin melakukan tool call (DuckDuckGo search)
                    if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                        tool_calls.extend(chunk.tool_call_chunks)
                    else:
                        token = chunk.content
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
            except Exception as stream_err:
                err_str = str(stream_err).lower()
                # Tangkap jika model lokal di Ollama tidak mendukung native tool calling (HTTP 400 Bad Request)
                if "tool" in err_str or "400" in err_str or "support" in err_str:
                    print(f"[LLMService] Model tidak mendukung tools secara native ({stream_err}). Fallback ke chat standar...")
                    self.supports_tools = False
                    use_fallback = True
                else:
                    raise stream_err

            # Jika model tidak mendukung tools, jalankan standard chat stream sebagai fallback
            if use_fallback:
                full_response = ""
                stream = self.llm.astream(messages_to_send)
                async for chunk in stream:
                    token = chunk.content
                    full_response += token

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


            # Jika model memicu Tool Calling (Native Tool Call)
            if tool_calls:
                # Gabungkan chunk tool calls menjadi satu call utuh
                print(f"[LLMService] Model memicu native tool call...")
                # Format sederhana untuk mengekstrak nama fungsi dan argumen
                tool_name = tool_calls[0].get('name')
                tool_input = tool_calls[0].get('args', '')
                tool_call_id = tool_calls[0].get('id', 'call_1')
                
                # Jika model memanggil DuckDuckGo
                if tool_name == "duckduckgo_search":
                    # Ekstrak query dari argumen
                    query = tool_input
                    if isinstance(tool_input, dict):
                        query = tool_input.get('query', '')
                    
                    print(f"[LLMService] Mengeksekusi pencarian DuckDuckGo untuk: '{query}'")
                    loop = asyncio.get_event_loop()
                    tool_result = await loop.run_in_executor(None, self.search_tool.run, query)
                    
                    # Tambahkan pesan Tool Call dan respons Tool ke pesan yang dikirim
                    ai_tool_msg = AIMessage(
                        content="",
                        tool_calls=[{
                            "name": tool_name,
                            "args": tool_input,
                            "id": tool_call_id
                        }]
                    )
                    tool_response_msg = ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call_id
                    )
                    
                    messages_to_send.append(ai_tool_msg)
                    messages_to_send.append(tool_response_msg)
                    
                    # Buat stream baru dengan menyertakan hasil pencarian tool
                    print(f"[LLMService] Melanjutkan streaming dengan hasil pencarian...")
                    final_stream = self.llm.astream(messages_to_send)
                    
                    async for chunk in final_stream:
                        token = chunk.content
                        full_response += token

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

            # Pembersihan tag ekspresi
            clean_response = re.sub(
                r'\s*\[EXPRESSION:\w+\]\s*', '', full_response
            )
            
            # Cari dan simpan memori jika ada
            mem_match = re.search(r'\[MEMORY:(.*?)\]', clean_response)
            if mem_match:
                fact_to_remember = mem_match.group(1).strip()
                self.memory.save_memory(fact_to_remember)
                
            clean_response = re.sub(
                r'\s*\[MEMORY:.*?\]\s*', '', clean_response
            ).strip()

            # Cari ekspresi akhir
            final_expression = "neutral"
            expr_match = re.search(
                r'\[EXPRESSION:(\w+)\]', full_response
            )
            if expr_match:
                final_expression = expr_match.group(1)

            # Simpan respons asisten ke riwayat percakapan sebagai AIMessage
            self.conversation_history.append(AIMessage(content=clean_response))

            # Pemicu Perangkuman Riwayat Percakapan (Memory Summarization) secara Asinkron di latar belakang
            asyncio.create_task(self._summarize_history())

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

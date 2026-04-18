"""
Gemma-Aura Backend — FastAPI WebSocket Server
Main entry point for the AI backend services.
"""
import asyncio
import json
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import HOST, PORT
from services.llm_service import LLMService
from services.stt_service import STTService
from services.tts_service import TTSService
from services.expression_parser import ExpressionParser

# ─── Initialize App ──────────────────────────────────────────────────────────
app = FastAPI(title="Gemma-Aura Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Initialize Services ────────────────────────────────────────────────────
llm_service = LLMService()
stt_service = STTService()
tts_service = TTSService()
expression_parser = ExpressionParser()


# ─── Health Check ────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    ollama_ok = await llm_service.check_connection()
    return {
        "status": "ok",
        "ollama_connected": ollama_ok,
        "stt_loaded": stt_service.is_loaded(),
        "tts_available": tts_service.is_available(),
    }


# ─── WebSocket Endpoint ──────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time communication.

    Message types (from client):
    - {"type": "chat", "text": "..."}           → Text chat
    - {"type": "audio", "data": "base64..."}    → Voice input (STT → Chat)
    - {"type": "reset"}                         → Reset conversation
    - {"type": "ping"}                          → Keep alive

    Response types (to client):
    - {"type": "token", "text": "...", "expression": "...", "done": false}
    - {"type": "response_complete", "text": "...", "expression": "..."}
    - {"type": "audio_response", "data": "base64...", "format": "wav"}
    - {"type": "stt_result", "text": "..."}
    - {"type": "status", "state": "thinking|speaking|idle"}
    - {"type": "error", "message": "..."}
    """
    await websocket.accept()
    print("[WS] Client connected")

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "reset":
                llm_service.reset_conversation()
                await websocket.send_json({
                    "type": "status",
                    "state": "idle",
                    "message": "Conversation reset",
                })

            elif msg_type == "chat":
                await handle_chat(websocket, message.get("text", ""))

            elif msg_type == "audio":
                await handle_audio(websocket, message.get("data", ""))

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass


async def handle_chat(websocket: WebSocket, text: str):
    """Handle text chat message with streaming response."""
    if not text.strip():
        return

    # Notify client: thinking
    await websocket.send_json({
        "type": "status",
        "state": "thinking",
    })

    full_response = ""

    # Stream response tokens
    async for chunk in llm_service.chat_stream(text):
        if chunk.get("error"):
            await websocket.send_json({
                "type": "error",
                "message": chunk["error"],
            })
            return

        if not chunk["done"]:
            await websocket.send_json({
                "type": "token",
                "text": chunk["token"],
                "expression": chunk.get("expression"),
                "done": False,
            })
        else:
            full_response = chunk.get("full_response", "")
            final_expression = chunk.get("expression", "neutral")

            # Parse expression parameters for Live2D
            expr_data = expression_parser.parse_expression(
                f"[EXPRESSION:{final_expression}]"
            )

            await websocket.send_json({
                "type": "response_complete",
                "text": full_response,
                "expression": final_expression,
                "expression_params": expr_data["params"],
                "transition_duration": expr_data["transition_duration"],
            })

    # Generate TTS audio if available
    if tts_service.is_available() and full_response:
        await websocket.send_json({
            "type": "status",
            "state": "speaking",
        })

        # Run TTS in thread pool to not block
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(
            None, tts_service.synthesize, full_response
        )

        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await websocket.send_json({
                "type": "audio_response",
                "data": audio_b64,
                "format": "wav",
            })

    # Notify client: idle
    await websocket.send_json({
        "type": "status",
        "state": "idle",
    })


async def handle_audio(websocket: WebSocket, audio_b64: str):
    """Handle voice input: STT → Chat → TTS."""
    if not audio_b64:
        return

    # Notify client: listening/processing
    await websocket.send_json({
        "type": "status",
        "state": "listening",
    })

    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_b64)

        # Run STT in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, stt_service.transcribe, audio_bytes
        )

        transcribed_text = result.get("text", "")

        if not transcribed_text:
            await websocket.send_json({
                "type": "error",
                "message": "Tidak dapat mengenali suara. Coba lagi.",
            })
            return

        # Send STT result back to client
        await websocket.send_json({
            "type": "stt_result",
            "text": transcribed_text,
            "confidence": result.get("confidence", 0),
        })

        # Process as chat
        await handle_chat(websocket, transcribed_text)

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Audio processing error: {str(e)}",
        })


# ─── Startup / Shutdown ──────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Pre-load models on startup."""
    print("=" * 50)
    print("  Gemma-Aura Backend Starting...")
    print("=" * 50)

    # Check Ollama connection
    ollama_ok = await llm_service.check_connection()
    if ollama_ok:
        print(f"[LLM] [OK] Ollama connected, model: {llm_service.model}")
    else:
        print(f"[LLM] [FAIL] Ollama not available! Run: ollama pull {llm_service.model}")

    # Lazy-load STT (will load on first request)
    print(f"[STT] Faster-Whisper ({stt_service.__class__.__name__}) ready (lazy load)")

    # Try loading TTS
    tts_service.load_model()

    print("=" * 50)
    print(f"  Server ready at ws://{HOST}:{PORT}/ws")
    print("=" * 50)


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )

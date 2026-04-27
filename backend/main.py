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
import re

from config import (
    HOST, PORT, OLLAMA_MODEL, SYSTEM_PROMPT, 
    EXPRESSION_PARAMS, OLLAMA_OPTIONS
)
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
is_warming_up = True
active_websockets = set()

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
    active_websockets.add(websocket)
    print("[WS] Client connected")

    if is_warming_up:
        await websocket.send_json({"type": "startup_progress", "message": "Sedang mensinkronisasi dengan model..."})
    else:
        await websocket.send_json({"type": "status", "state": "idle"})

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
    finally:
        active_websockets.discard(websocket)

import asyncio

# Lock to prevent concurrent websocket.send_json calls when background tasks finish
ws_lock = asyncio.Lock()

async def safe_send(websocket: WebSocket, data: dict):
    """Safely send JSON to websocket, preventing concurrent sends."""
    async with ws_lock:
        try:
            await websocket.send_json(data)
        except Exception as e:
            print(f"[WS] Send error: {e}")

async def synthesize_and_send(websocket: WebSocket, text: str, expression: str):
    """Background task to synthesize TTS and send it without blocking LLM stream."""
    audio_b64 = None
    if tts_service.is_available():
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(
            None, tts_service.synthesize, text
        )
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    await safe_send(websocket, {
        "type": "sentence",
        "text": text,
        "audio": audio_b64,
        "expression": expression,
    })

async def handle_chat(websocket: WebSocket, text: str):
    """Handle text chat message with streaming response."""
    if not text.strip():
        return

    # Notify client: thinking
    await safe_send(websocket, {
        "type": "status",
        "state": "thinking",
    })

    full_response = ""
    sentence_buffer = ""

    # Stream response tokens
    async for chunk in llm_service.chat_stream(text):
        if chunk.get("error"):
            await safe_send(websocket, {
                "type": "error",
                "message": chunk["error"],
            })
            return

        if not chunk["done"]:
            token = chunk["token"]
            
            # Send token immediately to frontend for TTFT < 500ms
            # We don't wait for sentence boundary to show text anymore
            await safe_send(websocket, {
                "type": "token",
                "text": token
            })
            
            sentence_buffer += token

            # Periksa apakah kita mencapai batas kalimat atau klausa (titik, koma, tanya, seru)
            # Menambahkan koma (', ') agar TTS terpicu lebih awal (per klausa) tanpa menunggu satu kalimat penuh
            if any(punc in token for punc in ['. ', '? ', '! ', '\n', ', ']) and len(sentence_buffer.strip()) > 2:
                clean_sentence = sentence_buffer.strip()
                sentence_buffer = ""

                # Bersihkan tag sistem dan teks action (*tersenyum*) sebelum diucapkan
                tts_text = re.sub(r'\[.*?\]', '', clean_sentence)
                tts_text = re.sub(r'\*.*?\*', '', tts_text).strip()

                if tts_text:
                    # Dispatch background task for TTS to avoid blocking the LLM stream
                    asyncio.create_task(
                        synthesize_and_send(websocket, tts_text, chunk.get("expression", "neutral"))
                    )
        else:
            # Process remaining buffer if any
            if sentence_buffer.strip():
                clean_sentence = sentence_buffer.strip()
                tts_text = re.sub(r'\[.*?\]', '', clean_sentence)
                tts_text = re.sub(r'\*.*?\*', '', tts_text).strip()
                if tts_text:
                    asyncio.create_task(
                        synthesize_and_send(websocket, tts_text, chunk.get("expression", "neutral"))
                    )

            full_response = chunk.get("full_response", "")
            final_expression = chunk.get("expression", "neutral")

            # Parse expression parameters for Live2D
            expr_data = expression_parser.parse_expression(
                f"[EXPRESSION:{final_expression}]"
            )

            await safe_send(websocket, {
                "type": "response_complete",
                "text": full_response,
                "expression": final_expression,
                "expression_params": expr_data["params"],
                "transition_duration": expr_data["transition_duration"],
            })

    # Notify client: idle
    await safe_send(websocket, {
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
async def broadcast_progress(message: str):
    for ws in list(active_websockets):
        try:
            await ws.send_json({"type": "startup_progress", "message": message})
        except Exception:
            pass

async def warmup_models():
    """Background task to pre-load models into VRAM/Memory."""
    print("[Warmup] Memulai pemanasan model di background...")
    await broadcast_progress("Memanaskan inti kecerdasan buatan...")
    
    # 1. Warmup LLM (Gemma) with the actual system prompt to cache it
    try:
        system_prompt = llm_service.conversation_history[0]["content"] if llm_service.conversation_history else "Anda adalah asisten AI."
        await llm_service.client.chat(
            model=llm_service.model, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "hi"}
            ],
            keep_alive="-1",
            options=OLLAMA_OPTIONS
        )
        print("--- Warmup LLM OK ---")
        await broadcast_progress("Model AI siap!")
    except Exception as e:
        print(f"--- Warmup LLM FAILED: {e} ---")
        await broadcast_progress("Gagal memuat model AI.")
        
    # 2. Warmup TTS (Piper)
    await broadcast_progress("Memuat pita suara (TTS)...")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, tts_service.load_model)
        if tts_service.is_available():
            await loop.run_in_executor(None, tts_service.synthesize, "siap")
            print("--- Warmup TTS OK ---")
        else:
            print("--- Warmup TTS skipped: Model not available ---")
    except Exception as e:
        print(f"--- Warmup TTS FAILED: {e} ---")

    # 3. Warmup STT (Faster-Whisper)
    await broadcast_progress("Memuat sistem pendengaran (STT)...")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, stt_service.load_model)
        print("--- Warmup STT OK ---")
    except Exception as e:
        print(f"--- Warmup STT FAILED: {e} ---")

    global is_warming_up
    is_warming_up = False
    
    # Beritahu semua client bahwa warmup selesai
    for ws in list(active_websockets):
        try:
            await ws.send_json({"type": "status", "state": "idle"})
        except Exception:
            pass

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

    # Jalankan seluruh proses berat di background agar server cepat siap
    asyncio.create_task(warmup_models())
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, llm_service.memory.ingest_documents)

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

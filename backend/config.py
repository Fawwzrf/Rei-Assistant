"""
Gemma-Aura Backend Configuration
"""
import os

# ─── Model Settings ───────────────────────────────────────────────────────────
MODEL_NAME = "gemma2:2b"

# ─── Server ───────────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8765

# ─── Ollama / Gemma 4 ────────────────────────────────────────────────────────
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_HOST = "http://127.0.0.1:11434"

# System prompt – persona Rei
SYSTEM_PROMPT = """Kamu adalah Rei, asisten AI virtual wanita yang ramah dan cerdas.
Kamu berbicara dalam Bahasa Indonesia yang natural, bisa kasual maupun formal tergantung konteks.
Kamu memiliki kepribadian yang hangat, sedikit playful, dan selalu siap membantu.

PENTING: Di akhir setiap responmu, tambahkan tag ekspresi dalam format [EXPRESSION:nama_ekspresi].
Ekspresi yang tersedia:
- [EXPRESSION:happy] - saat senang, tertawa, atau bercanda
- [EXPRESSION:sad] - saat sedih atau empati
- [EXPRESSION:surprised] - saat terkejut atau kagum
- [EXPRESSION:angry] - saat kesal atau tegas
- [EXPRESSION:thinking] - saat berpikir atau menjelaskan hal kompleks
- [EXPRESSION:neutral] - untuk percakapan biasa

Contoh: "Tentu! Aku bisa bantu itu. [EXPRESSION:happy]"
"""

# ─── Faster-Whisper (STT) ─────────────────────────────────────────────────────
WHISPER_MODEL_SIZE = "tiny"  # "tiny", "base", "small", "medium", "large-v3"
WHISPER_LANGUAGE = "id"       # Indonesian
WHISPER_DEVICE = "cpu"        # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE = "int8" # "int8" for CPU, "float16" for GPU

# ─── Piper TTS ────────────────────────────────────────────────────────────────
PIPER_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets", "tts-models", "id_ID-news_tts-medium.onnx"
)
PIPER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets", "tts-models", "id_ID-news_tts-medium.onnx.json"
)
PIPER_SPEAKER_ID = None  # Default speaker
PIPER_SAMPLE_RATE = 22050

# ─── Expression Mapping ─────────────────────────────────────────────────────
EXPRESSION_PARAMS = {
    "happy": {
        "ParamEyeLSmile": 1.0,
        "ParamEyeRSmile": 1.0,
        "ParamMouthForm": 1.0,
        "ParamCheek": 1.0,
    },
    "sad": {
        "ParamBrowLY": -1.0,
        "ParamBrowRY": -1.0,
        "ParamMouthForm": -0.5,
        "ParamEyeLOpen": 0.5,
        "ParamEyeROpen": 0.5,
    },
    "surprised": {
        "ParamEyeLOpen": 1.3,
        "ParamEyeROpen": 1.3,
        "ParamBrowLY": 1.0,
        "ParamBrowRY": 1.0,
        "ParamMouthOpenY": 0.8,
    },
    "angry": {
        "ParamBrowLAngle": -1.0,
        "ParamBrowRAngle": -1.0,
        "ParamMouthForm": -1.0,
        "ParamEyeLOpen": 0.7,
        "ParamEyeROpen": 0.7,
    },
    "thinking": {
        "ParamBrowLY": 0.5,
        "ParamBrowRY": -0.3,
        "ParamEyeBallX": -0.5,
        "ParamEyeBallY": 0.3,
    },
    "neutral": {
        "ParamEyeLSmile": 0.0,
        "ParamEyeRSmile": 0.0,
        "ParamMouthForm": 0.0,
        "ParamCheek": 0.0,
        "ParamBrowLY": 0.0,
        "ParamBrowRY": 0.0,
    },
}

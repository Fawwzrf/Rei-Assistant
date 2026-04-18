"""
STT Service — Speech-to-Text using Faster-Whisper
Transcribes audio to Indonesian text locally.
"""
import io
import numpy as np
from faster_whisper import WhisperModel
from config import (
    WHISPER_MODEL_SIZE,
    WHISPER_LANGUAGE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)


class STTService:
    def __init__(self):
        self.model = None
        self._loaded = False

    def load_model(self):
        """Load Whisper model (lazy loading on first use)."""
        if not self._loaded:
            print(f"[STT] Loading Faster-Whisper model: {WHISPER_MODEL_SIZE}...")
            self.model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            self._loaded = True
            print("[STT] Model loaded successfully.")

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> dict:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw PCM audio data (16-bit, mono)
            sample_rate: Audio sample rate (default 16000)

        Returns:
            dict with 'text', 'language', 'confidence'
        """
        self.load_model()

        try:
            # Convert bytes to numpy array (16-bit PCM → float32)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(
                np.float32
            ) / 32768.0

            segments, info = self.model.transcribe(
                audio_np,
                language=WHISPER_LANGUAGE,
                beam_size=5,
                vad_filter=True,  # Filter out silence
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                ),
            )

            # Collect all segments
            full_text = ""
            for segment in segments:
                full_text += segment.text

            return {
                "text": full_text.strip(),
                "language": info.language,
                "confidence": info.language_probability,
                "duration": info.duration,
            }

        except Exception as e:
            return {
                "text": "",
                "error": str(e),
                "language": WHISPER_LANGUAGE,
                "confidence": 0.0,
            }

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded

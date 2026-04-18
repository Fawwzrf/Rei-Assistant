"""
TTS Service — Text-to-Speech using Piper TTS
Generates Indonesian speech audio locally.
"""
import io
import wave
import os
from config import PIPER_MODEL_PATH, PIPER_CONFIG_PATH, PIPER_SAMPLE_RATE


class TTSService:
    def __init__(self):
        self.voice = None
        self._loaded = False
        self._available = False

    def load_model(self):
        """Load Piper TTS voice model (lazy loading)."""
        if self._loaded:
            return

        # Check if model files exist
        if not os.path.exists(PIPER_MODEL_PATH):
            print(f"[TTS] Model not found: {PIPER_MODEL_PATH}")
            print("[TTS] Download it from: https://huggingface.co/rhasspy/piper-voices")
            print("[TTS] Place files in: assets/tts-models/")
            self._available = False
            return

        try:
            from piper import PiperVoice
            print(f"[TTS] Loading Piper model: {PIPER_MODEL_PATH}...")
            self.voice = PiperVoice.load(
                PIPER_MODEL_PATH,
                config_path=PIPER_CONFIG_PATH,
            )
            self._loaded = True
            self._available = True
            print("[TTS] Model loaded successfully.")
        except Exception as e:
            print(f"[TTS] Failed to load model: {e}")
            self._available = False

    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to WAV audio bytes.

        Args:
            text: Indonesian text to speak

        Returns:
            WAV audio as bytes
        """
        self.load_model()

        if not self._available:
            return b""

        try:
            # Create in-memory WAV file
            wav_buffer = io.BytesIO()

            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(PIPER_SAMPLE_RATE)

                audio_stream = self.voice.synthesize(text)
                for chunk in audio_stream:
                    wav_file.writeframes(chunk.audio_int16_bytes)

            wav_buffer.seek(0)
            return wav_buffer.read()

        except Exception as e:
            print(f"[TTS] Synthesis error: {e}")
            return b""

    def is_available(self) -> bool:
        """Check if TTS model is loaded and available."""
        return self._available

    def is_loaded(self) -> bool:
        """Check if model loading was attempted."""
        return self._loaded

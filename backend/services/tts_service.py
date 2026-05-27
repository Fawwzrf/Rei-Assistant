"""
TTS Service — Text-to-Speech using Microsoft Edge-TTS
Generates high-quality natural speech via API.
"""
import io
import os
import asyncio
import edge_tts
from config import EDGE_TTS_VOICE, EDGE_TTS_PITCH, EDGE_TTS_RATE


class TTSService:
    def __init__(self):
        self._available = True # Edge-TTS is API based, assumed available if internet exists

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to MP3/WAV audio bytes using Edge-TTS.
        Loads settings dynamically from tts_settings.json for live tuning.
        """
        # --- LIVE TUNING: Load settings from JSON on every call ---
        import json
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tts_settings.json")
        
        # Default values from config if file fails
        voice = EDGE_TTS_VOICE
        pitch = EDGE_TTS_PITCH
        rate = EDGE_TTS_RATE

        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    data = json.load(f)
                    voice = data.get("voice", voice)
                    pitch = data.get("pitch", pitch)
                    rate = data.get("rate", rate)
        except Exception as e:
            print(f"[TTS] Error loading live settings: {e}")

        print(f"[TTS] Synthesizing with {pitch} pitch, {rate} rate...")
        
        try:
            communicate = edge_tts.Communicate(
                text, 
                voice,
                pitch=pitch,
                rate=rate
            )
            
            # Use memory buffer for audio
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            if audio_data:
                print(f"[TTS] Successfully generated {len(audio_data)} bytes.")
            else:
                print("[TTS] Generated empty audio data.")
                
            return audio_data

        except Exception as e:
            print(f"[TTS] Edge-TTS error: {e}")
            import traceback
            traceback.print_exc()
            return b""

    def is_available(self) -> bool:
        return self._available

    def is_loaded(self) -> bool:
        return True


"""Selects concrete service implementations based on the *_PROVIDER env flags.

This is the single place that knows about every provider. Add a new provider by
writing its module and adding one line here.
"""

from app.config import settings
from app.services.base import STTService, TTSService, VisionService


def get_stt() -> STTService:
    if settings.stt_provider == "elevenlabs":
        from app.services.stt_elevenlabs import ElevenLabsSTT

        return ElevenLabsSTT()
    if settings.stt_provider == "wispr":
        from app.services.stt_wispr import WisprSTT

        return WisprSTT()
    from app.services.stt_mock import MockSTT

    return MockSTT()


def get_vision() -> VisionService:
    if settings.vision_provider == "gemini":
        from app.services.vision_gemini import GeminiVision

        return GeminiVision()
    if settings.vision_provider == "fal":
        from app.services.vision_fal import FalVision

        return FalVision()
    if settings.vision_provider == "qwen":
        from app.services.vision_qwen import QwenVision

        return QwenVision()
    from app.services.vision_mock import MockVision

    return MockVision()


def get_tts() -> TTSService:
    if settings.tts_provider == "elevenlabs":
        from app.services.tts_elevenlabs import ElevenLabsTTS

        return ElevenLabsTTS()
    from app.services.tts_mock import MockTTS

    return MockTTS()

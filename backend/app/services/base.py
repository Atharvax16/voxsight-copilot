"""Service protocols. Each external AI service implements one of these.

Keeping these as narrow async interfaces means the orchestrator never knows or
cares whether it's talking to a mock or a live API — tomorrow we just swap the
provider in .env and nothing else changes.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class STTService(Protocol):
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Turn recorded audio into a text question."""
        ...


@runtime_checkable
class VisionService(Protocol):
    async def describe(self, image_b64: str, question: str) -> str:
        """Answer `question` about the given base64 image (data URL or raw b64)."""
        ...


@runtime_checkable
class TTSService(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """Turn text into spoken audio bytes (WAV or MP3)."""
        ...

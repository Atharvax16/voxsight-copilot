"""Live STT stub.

NOTE: Wispr Flow is primarily a desktop dictation product and does not expose a
clean public transcription REST API. This module is written against a generic
multipart "upload audio, get transcript" shape. If Wispr has no usable endpoint
tomorrow, swap the URL/auth here for OpenAI Whisper
(POST https://api.openai.com/v1/audio/transcriptions, model=whisper-1) — the
orchestrator never needs to change.

# TODO verify against live API — endpoint, auth header, and response shape are guesses.
"""

import httpx

from app.config import settings

WISPR_ENDPOINT = "https://api.wispr.ai/v1/transcribe"  # TODO confirm real URL


class WisprSTT:
    async def transcribe(self, audio_bytes: bytes) -> str:
        headers = {"Authorization": f"Bearer {settings.wispr_api_key}"}
        files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(WISPR_ENDPOINT, headers=headers, files=files)
            resp.raise_for_status()
            data = resp.json()
        # TODO adjust to real response schema.
        return data.get("text", "")

"""Live STT via ElevenLabs Scribe.

Used in place of Wispr Flow (whose API is exclusive-access / org-verified only).
Same ElevenLabs key powers both this and TTS.

Endpoint: POST https://api.elevenlabs.io/v1/speech-to-text (multipart).
Response: JSON with a `text` field (SpeechToTextChunkResponseModel).
"""

import httpx

from app.config import settings

SCRIBE_ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"


class ElevenLabsSTT:
    async def transcribe(self, audio_bytes: bytes) -> str:
        headers = {"xi-api-key": settings.elevenlabs_api_key}
        # Browser MediaRecorder typically produces webm/opus; Scribe sniffs the
        # container, so the filename/content-type is a hint, not a hard rule.
        files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
        data = {"model_id": settings.elevenlabs_stt_model}
        # Force a language so Scribe doesn't mis-detect accented English as
        # another language (e.g. Hindi). Blank = let Scribe auto-detect.
        if settings.elevenlabs_stt_language:
            data["language_code"] = settings.elevenlabs_stt_language
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SCRIBE_ENDPOINT, headers=headers, files=files, data=data
            )
            resp.raise_for_status()
            payload = resp.json()
        return payload.get("text", "")

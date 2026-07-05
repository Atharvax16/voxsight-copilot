"""Live TTS via ElevenLabs.

# TODO verify against live API — confirm voice id and that the key is active.
Returns MP3 bytes, which browsers play natively.
"""

import httpx

from app.config import settings


class ElevenLabsTTS:
    async def synthesize(self, text: str) -> bytes:
        voice_id = settings.elevenlabs_voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": settings.elevenlabs_model,  # flash v2.5 = lowest latency
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content

"""Live Vision via Google Gemini (AI Studio generateContent endpoint).

Chosen as the vision provider because a free AI Studio key is instant, works
internationally, and Gemini's image understanding is strong. Same describe()
interface as the other vision providers, so the orchestrator is unchanged.

Endpoint: POST .../models/{model}:generateContent?key=API_KEY
"""

import httpx

from app.config import settings

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiVision:
    async def describe(self, image_b64: str, question: str) -> str:
        # Accept a full data URL or a raw base64 string; split out mime + data.
        mime = "image/jpeg"
        data = image_b64
        if image_b64.startswith("data:"):
            header, _, data = image_b64.partition(",")
            # header looks like: data:image/png;base64
            mime = header[5:].split(";")[0] or mime

        url = f"{BASE}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": question},
                        {"inline_data": {"mime_type": mime, "data": data}},
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 300, "temperature": 0.4},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()

        return body["candidates"][0]["content"]["parts"][0]["text"]

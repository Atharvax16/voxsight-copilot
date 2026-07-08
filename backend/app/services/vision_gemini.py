"""Live Vision via Google Gemini (AI Studio generateContent endpoint).

Chosen as the vision provider because a free AI Studio key is instant, works
internationally, and Gemini's image understanding is strong. Same describe()
interface as the other vision providers, so the orchestrator is unchanged.

Endpoint: POST .../models/{model}:generateContent?key=API_KEY
"""

import asyncio

import httpx

from app.config import settings

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Transient statuses worth retrying — Gemini occasionally 503s under load.
_RETRY = {429, 500, 502, 503, 504}


class GeminiVision:
    async def describe(self, image_b64: str, question: str) -> str:
        # Accept a full data URL or a raw base64 string; split out mime + data.
        mime = "image/jpeg"
        data = image_b64
        if image_b64.startswith("data:"):
            header, _, data = image_b64.partition(",")
            # header looks like: data:image/png;base64
            mime = header[5:].split(";")[0] or mime

        # Text-only intents (remember/recall/remind) arrive with no frame — send
        # just the text, since Gemini rejects an empty inline_data part.
        parts: list[dict] = [{"text": question}]
        if data:
            parts.append({"inline_data": {"mime_type": mime, "data": data}})

        url = f"{BASE}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": 300,
                "temperature": 0.4,
                # gemini-2.5-flash "thinks" by default, which burns the token
                # budget and truncates the answer. Disable it: faster + complete,
                # and this is a describe-what-you-see task, not a reasoning one.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        async with httpx.AsyncClient(timeout=90) as client:
            # Retry transient overloads / rate limits (503/429/…) with a growing
            # backoff so a momentary Gemini blip or a rate-limit window clears
            # instead of killing the turn.
            delays = [2.0, 6.0]
            for attempt in range(len(delays) + 1):
                resp = await client.post(url, json=payload)
                if resp.status_code in _RETRY and attempt < len(delays):
                    await asyncio.sleep(delays[attempt])
                    continue
                break
            resp.raise_for_status()
            body = resp.json()

        return body["candidates"][0]["content"]["parts"][0]["text"]

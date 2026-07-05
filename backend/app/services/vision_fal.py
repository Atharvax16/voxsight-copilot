"""Live Vision via fal.ai — replaces Qwen when a direct DashScope key isn't available.

fal proxies several vision-language models (Gemini, Claude, Qwen-VL, Llama-Vision)
behind one endpoint, selected by the `model` field. We pass the camera frame as a
base64 data URI, so no separate image upload step is needed.

Endpoint: POST https://fal.run/{FAL_VISION_MODEL}  (synchronous)
Auth:     Authorization: Key {FAL_KEY}
Response: {"output": "...text...", ...}

Everything (fal slug + underlying model) is env-configurable so we can swap models
without code changes if a route is deprecated.
"""

import httpx

from app.config import settings


class FalVision:
    async def describe(self, image_b64: str, question: str) -> str:
        image_url = image_b64
        if not image_url.startswith("data:"):
            image_url = f"data:image/jpeg;base64,{image_b64}"

        url = f"https://fal.run/{settings.fal_vision_model}"
        headers = {
            "Authorization": f"Key {settings.fal_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.fal_vision_llm,
            "prompt": question,
            "image_urls": [image_url],
            "max_tokens": 300,
            "priority": "latency",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Primary shape is {"output": "..."}; fall back to common alternatives.
        if isinstance(data, dict):
            if data.get("output"):
                return data["output"]
            if data.get("text"):
                return data["text"]
        return str(data)

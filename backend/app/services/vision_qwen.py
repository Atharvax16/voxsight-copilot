"""Live Vision via Alibaba Qwen-VL, using the DashScope OpenAI-compatible endpoint.

# TODO verify against live API — confirm base URL region (intl vs cn), model name,
# and that your key has vision access. Response parsing assumes OpenAI chat shape.
"""

import httpx

from app.config import settings

# International endpoint. Use dashscope.aliyuncs.com (no -intl) for the China region.
QWEN_ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


class QwenVision:
    async def describe(self, image_b64: str, question: str) -> str:
        # Accept either a raw base64 string or a full data URL.
        image_url = image_b64
        if not image_url.startswith("data:"):
            image_url = f"data:image/jpeg;base64,{image_b64}"

        payload = {
            "model": settings.qwen_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": question},
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.qwen_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(QWEN_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

"""Mock Vision — returns a plausible scene description without touching any API.

It ignores the actual image (no vision model without a key) but echoes the real
question so it's obvious the pipeline is live and this is just placeholder output.
Swap VISION_PROVIDER=qwen tomorrow to describe the real camera frame.
"""

import asyncio


class MockVision:
    async def describe(self, image_b64: str, question: str) -> str:
        await asyncio.sleep(0.2)  # pretend we called a vision model
        # The orchestrator passes a templated prompt ending in "Question: <asked>".
        asked = question.split("Question:", 1)[-1].strip() or "your surroundings"
        return (
            f"[Mock vision] You asked: \"{asked}\". A real answer needs the Qwen "
            "vision key — set VISION_PROVIDER=qwen and I'll describe what the camera "
            "actually sees. For now: a wooden desk ahead, a laptop and a coffee mug "
            "to its right, bright daylight from a window on the left, path clear."
        )

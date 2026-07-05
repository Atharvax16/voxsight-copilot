"""Mock STT — returns a canned question without touching any API."""

import asyncio


class MockSTT:
    async def transcribe(self, audio_bytes: bytes) -> str:
        await asyncio.sleep(0.1)  # pretend we did some work
        # Rotate through a couple of plausible demo questions so the pipeline
        # feels alive even without real transcription.
        return "What is in front of me right now?"

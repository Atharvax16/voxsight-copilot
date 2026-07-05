"""The core pipeline: audio + image -> transcript -> vision answer -> speech.

Provider-agnostic. Services are resolved once at construction from the factory,
so switching mock->live is purely a config change.
"""

from dataclasses import dataclass

from app.services.factory import get_stt, get_tts, get_vision

PROMPT_TEMPLATE = (
    "You are VoxSight, a calm, concise assistant for a visually impaired person. "
    "Based on the image, answer their question in 1-3 short spoken sentences. "
    "Lead with what matters for safety and orientation (obstacles, distances, "
    "directions). Question: {question}"
)


@dataclass
class Turn:
    transcript: str
    answer: str
    audio: bytes


class Orchestrator:
    def __init__(self) -> None:
        self.stt = get_stt()
        self.vision = get_vision()
        self.tts = get_tts()

    async def run(
        self, image_b64: str, audio_bytes: bytes, transcript: str = ""
    ) -> Turn:
        # If the client already transcribed the question (e.g. browser Web Speech
        # API), use it and skip backend STT. Otherwise run the STT service.
        if not transcript:
            transcript = await self.stt.transcribe(audio_bytes)
        prompt = PROMPT_TEMPLATE.format(question=transcript)
        answer = await self.vision.describe(image_b64, prompt)
        audio = await self.tts.synthesize(answer)
        return Turn(transcript=transcript, answer=answer, audio=audio)

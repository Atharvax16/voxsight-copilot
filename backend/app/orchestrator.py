"""The core pipeline: audio + image -> transcript -> companion turn -> speech.

Provider-agnostic. Services are resolved once at construction from the factory,
so switching mock->live is purely a config change. The vision model doubles as
the companion brain: one call decides intent, produces the spoken reply, and
emits side-effects (see app/companion.py).
"""

from dataclasses import dataclass

from app import companion
from app.config import settings
from app.demo import RecordingStore
from app.services.factory import get_stt, get_tts, get_vision


@dataclass
class Turn:
    transcript: str
    answer: str
    audio: bytes
    mime: str = "audio/mpeg"
    intent: str = "describe"


class Orchestrator:
    def __init__(self) -> None:
        self.mode = settings.demo_mode
        self.store = RecordingStore()
        # In replay mode we never touch the providers, so don't construct them.
        if self.mode != "replay":
            self.stt = get_stt()
            self.vision = get_vision()
            self.tts = get_tts()

    async def run(
        self, image_b64: str, audio_bytes: bytes, transcript: str = ""
    ) -> Turn:
        # --- replay: serve a saved response, no API calls ---
        if self.mode == "replay":
            rec = self.store.match(transcript)
            if rec is None:
                raise RuntimeError(
                    "DEMO_MODE=replay but no recordings found. Capture some first "
                    "with DEMO_MODE=capture."
                )
            return Turn(rec.transcript or transcript, rec.answer, rec.audio, rec.mime)

        # --- live pipeline ---
        # If the client already transcribed the question (e.g. browser Web Speech
        # API), use it and skip backend STT. Otherwise run the STT service.
        if not transcript:
            transcript = await self.stt.transcribe(audio_bytes)

        # Phase 2/3 will feed real memory here; empty for now.
        facts: list[str] = []
        reminders: list[dict] = []

        prompt = companion.build_prompt(transcript, facts, reminders)
        raw = await self.vision.describe(image_b64, prompt)
        result = companion.parse(raw, transcript)

        # Side-effects (memory writes / reminders) are applied in Phase 2/3.

        answer = result.spoken
        audio = await self.tts.synthesize(answer)
        mime = "audio/wav" if settings.tts_provider == "mock" else "audio/mpeg"

        # --- capture: save the real response for later free replay ---
        if self.mode == "capture":
            self.store.save(transcript, answer, audio, mime)

        return Turn(
            transcript=transcript,
            answer=answer,
            audio=audio,
            mime=mime,
            intent=result.intent,
        )

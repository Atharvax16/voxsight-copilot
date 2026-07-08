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
from app.memory_store import MemoryStore
from app.nav_state import NavState
from app.services.factory import get_navigation, get_stt, get_tts, get_vision


@dataclass
class Turn:
    transcript: str
    answer: str
    audio: bytes
    mime: str = "audio/mpeg"
    intent: str = "describe"


@dataclass
class NavStep:
    """A turn-by-turn announcement produced from a location tick — no model call."""

    text: str
    audio: bytes
    mime: str = "audio/mpeg"


class Orchestrator:
    def __init__(self) -> None:
        self.mode = settings.demo_mode
        self.store = RecordingStore()
        self.memory = MemoryStore()
        self.nav = NavState()  # active route for this connection
        self.last_location: tuple[float, float] | None = None
        # In replay mode we never touch the providers, so don't construct them.
        if self.mode != "replay":
            self.stt = get_stt()
            self.vision = get_vision()
            self.tts = get_tts()
            self.navigation = get_navigation()

    async def run(
        self,
        image_b64: str,
        audio_bytes: bytes,
        transcript: str = "",
        location: dict | None = None,
    ) -> Turn:
        if location and "lat" in location and "lng" in location:
            self.last_location = (float(location["lat"]), float(location["lng"]))

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

        facts = self.memory.facts()
        reminders = self.memory.reminders()

        prompt = companion.build_prompt(transcript, facts, reminders)
        raw = await self.vision.describe(image_b64, prompt)
        result = companion.parse(raw, transcript)

        # Side-effects: persist anything the companion decided to remember.
        if result.memory_add:
            self.memory.add_fact(result.memory_add)
        # Reminders are applied in Phase 3.

        # Navigation side-effects. The routing engine is authoritative: for a
        # "navigate" turn we replace the model's acknowledgement with the real
        # first instruction; for "where am I" we prepend the reverse-geocoded place.
        answer = await self._apply_navigation(result)

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

    async def _apply_navigation(self, result: companion.CompanionResult) -> str:
        """Apply navigation intents and return the words to actually speak."""
        nav = result.navigation
        if nav and nav.get("action") == "stop":
            self.nav.clear()
            return result.spoken

        if nav and nav.get("action") == "start":
            if self.last_location is None:
                return (
                    "I need your location to navigate. Please turn on location "
                    "sharing and ask again."
                )
            destination = (nav.get("destination") or "").strip()
            if not destination:
                return "Where would you like to go?"
            coords = await self.navigation.geocode(
                destination, near=self.last_location
            )
            if coords is None:
                return f"I couldn't find {destination}. Could you say it another way?"
            route = await self.navigation.route(
                self.last_location, coords, destination
            )
            self.nav.start(route)
            return self.nav.first_instruction()

        if result.intent == "where_am_i" and self.last_location is not None:
            place = await self.navigation.reverse_geocode(*self.last_location)
            return f"You're near {place}. {result.spoken}"

        return result.spoken

    async def on_location(self, lat: float, lng: float) -> NavStep | None:
        """Feed a location update to the active route. Returns a spoken maneuver
        (or arrival) when one is due, otherwise None. No model or vision calls."""
        self.last_location = (lat, lng)
        if not self.nav.active():
            return None
        instruction = self.nav.update(lat, lng)
        if not instruction:
            return None
        # Replay mode constructs no providers; return text only (UI can show it).
        if self.mode == "replay":
            return NavStep(text=instruction, audio=b"", mime="audio/mpeg")
        audio = await self.tts.synthesize(instruction)
        mime = "audio/wav" if settings.tts_provider == "mock" else "audio/mpeg"
        return NavStep(text=instruction, audio=audio, mime=mime)

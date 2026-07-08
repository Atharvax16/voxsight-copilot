"""Service protocols. Each external AI service implements one of these.

Keeping these as narrow async interfaces means the orchestrator never knows or
cares whether it's talking to a mock or a live API — tomorrow we just swap the
provider in .env and nothing else changes.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # avoid a runtime import cycle; only needed for type hints
    from app.services.navigation import Route


@runtime_checkable
class STTService(Protocol):
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Turn recorded audio into a text question."""
        ...


@runtime_checkable
class VisionService(Protocol):
    async def describe(self, image_b64: str, question: str) -> str:
        """Answer `question` about the given base64 image (data URL or raw b64)."""
        ...


@runtime_checkable
class TTSService(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """Turn text into spoken audio bytes (WAV or MP3)."""
        ...


@runtime_checkable
class NavigationService(Protocol):
    """Walking navigation: turn place names into coordinates and coordinates into
    a step-by-step foot route. Deterministic — the routing engine navigates, the
    LLM only decides *that* the user wants to go somewhere and names where."""

    async def geocode(
        self, text: str, near: tuple[float, float] | None = None
    ) -> tuple[float, float] | None:
        """Resolve a spoken place ("the pharmacy on Dawson Street") to (lat, lng),
        biased toward `near` if given. None if nothing matches."""
        ...

    async def reverse_geocode(self, lat: float, lng: float) -> str:
        """Human-readable label for a coordinate ("Dawson Street, Dublin")."""
        ...

    async def route(
        self,
        start: tuple[float, float],
        dest: tuple[float, float],
        destination_label: str,
    ) -> "Route":
        """A walking route from `start` to `dest` as ordered maneuver steps."""
        ...

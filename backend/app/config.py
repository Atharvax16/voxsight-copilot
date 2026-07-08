"""Application settings, loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provider selection — `mock` tonight, real provider name tomorrow.
    stt_provider: str = "mock"
    vision_provider: str = "mock"
    tts_provider: str = "mock"

    # Demo mode: off | capture | replay. `replay` serves saved responses with
    # zero API calls — use it to rehearse/present/record video without burning
    # credits. `capture` records real responses so you can build the replay set.
    demo_mode: str = "off"

    # API keys (blank tonight).
    wispr_api_key: str = ""
    qwen_api_key: str = ""
    elevenlabs_api_key: str = ""
    fal_key: str = ""
    gemini_api_key: str = ""

    # Optional tuning.
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs "Rachel" default
    elevenlabs_model: str = "eleven_flash_v2_5"  # TTS: lowest latency for real-time
    elevenlabs_stt_model: str = "scribe_v1"  # STT (Scribe); set scribe_v2 if needed
    elevenlabs_stt_language: str = "en"  # force language; blank = auto-detect
    qwen_model: str = "qwen-vl-max"
    # fal.ai vision: which fal endpoint slug, and which underlying VLM it proxies.
    fal_vision_model: str = "fal-ai/any-llm/vision"
    fal_vision_llm: str = "google/gemini-2.5-flash-lite"  # fast + good vision
    gemini_model: str = "gemini-2.5-flash"  # fast + strong image understanding
    allowed_origins: str = "http://localhost:3000"

    # Navigation (Phase 1). `mock` runs fully offline (demo/tests); switch to
    # `openrouteservice` for live walking directions + geocoding. The routing
    # engine — not the LLM — produces turn-by-turn steps: cheap and reliable.
    nav_provider: str = "mock"
    openrouteservice_api_key: str = ""
    # Walk-mode tuning (metres). Announce a maneuver when the user comes within
    # `nav_announce_m` of it; declare arrival within `nav_arrive_m` of the end.
    nav_announce_m: float = 25.0
    nav_arrive_m: float = 15.0

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()

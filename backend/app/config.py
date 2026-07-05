"""Application settings, loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provider selection — `mock` tonight, real provider name tomorrow.
    stt_provider: str = "mock"
    vision_provider: str = "mock"
    tts_provider: str = "mock"

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
    qwen_model: str = "qwen-vl-max"
    # fal.ai vision: which fal endpoint slug, and which underlying VLM it proxies.
    fal_vision_model: str = "fal-ai/any-llm/vision"
    fal_vision_llm: str = "google/gemini-2.5-flash-lite"  # fast + good vision
    gemini_model: str = "gemini-2.5-flash"  # fast + strong image understanding
    allowed_origins: str = "http://localhost:3000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()

"""Speech service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings (e.g. ``INTELLIGENCE_SERVICE_URL``)."""

    intelligence_service_url: str = "http://intelligence:8002"
    intelligence_request_timeout_s: float = 120.0
    whisper_model: str = "base"
    max_upload_bytes: int = 25 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

"""Gateway configuration."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Upstream URLs and CORS (set via environment in Docker Compose)."""

    dataset_manager_url: str = "http://dataset-manager:8001"
    intelligence_service_url: str = "http://intelligence:8002"
    speech_service_url: str = "http://speech:8003"
    proxy_timeout_s: float = 300.0
    cors_origins: str = Field(
        default="*",
        description="Comma-separated origins, or * for any (dev only).",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _strip_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()

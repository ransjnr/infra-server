"""Gateway configuration."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Upstream URLs, CORS, PostgreSQL, and JWT (set via environment in Docker Compose)."""

    database_url: str = Field(
        default="postgresql://infra:infra@postgres:5432/infra",
        description="PostgreSQL URL (same DB as other services; gateway owns the `users` table).",
    )
    dataset_manager_url: str = "http://dataset-manager:8001"
    intelligence_service_url: str = "http://intelligence:8002"
    speech_service_url: str = "http://speech:8003"
    proxy_timeout_s: float = 300.0
    cors_origins: str = Field(
        default="*",
        description="Comma-separated origins, or * for any (dev only).",
    )
    jwt_secret: str = Field(
        default="dev-only-change-JWT_SECRET-in-production",
        description="HS256 signing key; set JWT_SECRET in production.",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7
    auth_enabled: bool = Field(
        default=True,
        description="If false, /api/* proxies do not require a Bearer token (local dev only).",
    )
    public_base_url: str = Field(
        default="",
        description="Public gateway URL (e.g. https://your-service.onrender.com) for OpenAPI servers in /docs.",
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

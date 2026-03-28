"""Settings for the intelligence service."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration (reads ``GHANA_NLP_API_KEY`` from the environment)."""

    ghana_nlp_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GHANA_NLP_API_KEY", "KHAYA_API_KEY"),
    )
    khaya_base_url: str = "https://translation.ghananlp.org"
    khaya_timeout_s: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

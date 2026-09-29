"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"

    ai_provider: str = "mock"
    ai_fallback_provider: str = ""

    gemini_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    mistral_api_key: str = ""

    database_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

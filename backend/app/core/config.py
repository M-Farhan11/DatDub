"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Hard ceiling regardless of MAX_ROWS_PER_TABLE.
ROWS_PER_TABLE_CEILING = 500_000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"

    ai_provider: str = "mock"
    ai_fallback_provider: str = ""

    gemini_api_key: str = ""
    gemini_model: str = ""
    groq_api_key: str = ""
    groq_model: str = ""
    ai_timeout_seconds: float = 30.0

    # comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    max_rows_per_table: int = 100_000
    max_datasets: int = 20
    dataset_ttl_minutes: int = 60

    allow_private_db_hosts: bool = False
    default_sample_limit: int = 200
    max_sample_limit: int = 1000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def row_cap(self) -> int:
        return min(self.max_rows_per_table, ROWS_PER_TABLE_CEILING)


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Shared kernel: application configuration loaded from environment only.

Phase 1: minimal settings required to boot backend + frontend.
No secrets are hardcoded; see `.env.example` for documented variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings (12-factor)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "northstar-worker"
    environment: str = "local"
    log_level: str = "INFO"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    frontend_url: str = "http://localhost:5173"

    # Optional: wired in later phases (DB roles, operator token, LLM).
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/northstar"
    operator_token: str = "local-operator-token"
    inception_api_key: str = ""
    inception_model: str = ""
    inception_base_url: str = "https://api.inceptionlabs.ai/v1"
    llm_timeout_s: float = 30.0
    llm_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so app code shares one parsed settings object."""
    return Settings()

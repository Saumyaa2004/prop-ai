"""
Prop AI - application settings.

Reads configuration from environment variables or the backend/.env file
and validates it with Pydantic. Secrets live in .env, never in code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder: this file is backend/app/config.py, so go up two levels.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All configuration Prop AI's backend needs, with types."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated variables instead of crashing
    )

    app_name: str = "Prop AI API"
    app_env: str = "development"
    database_url: str  # no default: the app must refuse to start without it

    # Browser origins allowed to call the API (scheme + host + port, exact match).
    # In .env, write JSON: CORS_ORIGINS=["http://localhost:5173"]
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse the same object afterwards."""
    return Settings()
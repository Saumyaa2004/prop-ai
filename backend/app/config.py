"""
Prop AI - application settings.

Reads configuration from environment variables or the backend/.env file
and validates it with Pydantic. Secrets live in .env, never in code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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

    # AI agent (Gemini free tier). Optional: search and details work without it.
    # SecretStr prints as '**********', so the key can't leak through logs.
    gemini_api_key: SecretStr | None = None
    # Verified 2026-10-14: 2.5-flash is closed to new users; 3.7/3.8 often return
    # 503 (overloaded) on the free tier. Fallback is used on 503/429.
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.5-flash-lite"

    # /chat rate limits: each message costs up to 6 Gemini calls (usually 2-3).
    # Per visitor (IP) per minute stops one person flooding; the per-day cap for
    # the whole site is what protects the quota from many IPs. Adjust per_day to
    # the key's real quota (shown in Google AI Studio).
    chat_per_minute: int = Field(default=5, ge=1)
    chat_per_day: int = Field(default=200, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse the same object afterwards."""
    return Settings()
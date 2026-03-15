from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_path() -> Path:
    """Resolve .env relative to server root so it's found when run from any cwd."""
    return Path(__file__).resolve().parent.parent / ".env"


class AISettings(BaseSettings):
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_TEMPERATURE: float = 0.0

    # Safety / perf
    MAX_RESUME_CHARS: int = 120_000

    model_config = SettingsConfigDict(
        env_file=_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()

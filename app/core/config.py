from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union


def _env_path() -> Path:
    """Resolve .env relative to server root so it's found when run from any cwd."""
    return Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "DishaSetu API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # APP
    APP_ENV: str = "development"
    DEBUG: bool = True

    # DATABASE
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dishasetu"

    # CORS — set in .env as JSON array or comma-separated, e.g. ["http://localhost:3000","http://127.0.0.1:3000"]
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # CLOUDINARY — set in .env only; no defaults to avoid leaking secrets
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # REDIS
    REDIS_URL: str = "redis://localhost:6379/0"

    # Embeddings
    RESUME_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Resume builder SSO (optional; falls back to SECRET_KEY if unset)
    RESUME_BUILDER_JWT_SECRET: str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                import json
                return json.loads(s)
            return [origin.strip() for origin in s.split(",")]
        return []

    model_config = SettingsConfigDict(
        env_file=_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

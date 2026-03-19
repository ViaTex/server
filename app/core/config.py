from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_path() -> Path:
    """Resolve .env relative to server root so it's found when run from any cwd."""
    return Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "DishaSetu API"
    PROJECT_NAME: str = "DishaSetu API"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "production"
    APP_DEBUG: bool = False
    DEBUG: bool = False
    APP_URL: str = "http://135.235.182.119:8000"
    VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dishasetu"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # CORS
    # Can be provided as comma-separated string or JSON array in .env
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://dishasetu.in",
        "https://www.dishasetu.in",
    ]

    # Mail configuration (kept minimal; values should come from .env)
    MAIL_MAILER: str = "smtp"
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_ENCRYPTION: str = "tls"
    MAIL_FROM_ADDRESS: str = "noreply@dishasetu.in"
    MAIL_FROM_NAME: str = "DishaSetu"

    # Frontend URL for links in emails
    FRONTEND_URL: str = "https://dishasetu.in"

    # Cloud / storage placeholders
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_BUCKET: str = ""

    # Embeddings
    RESUME_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Resume builder / SSO (optional; falls back to SECRET_KEY if unset)
    RESUME_BUILDER_JWT_SECRET: str = ""

    # Cloudinary — set in .env only; no defaults to avoid leaking secrets
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Groq (LLM + transcription)
    GROQ_API_KEY: str = ""
    GROQ_TRANSCRIPTION_MODEL: str = ""
    GROQ_ANALYSIS_MODEL: str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                import json

                return json.loads(s)
            return [origin.strip() for origin in s.split(",")]
        if isinstance(v, list):
            return v
        raise ValueError(v)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> str:
        if isinstance(v, str) and v:
            return v
        values = info.data
        user = values.get("POSTGRES_USER", "postgres")
        password = values.get("POSTGRES_PASSWORD", "postgres")
        server = values.get("POSTGRES_SERVER", "localhost")
        port = values.get("POSTGRES_PORT", "5432")
        db = values.get("POSTGRES_DB", "dishasetu")
        return f"postgresql://{user}:{password}@{server}:{port}/{db}"

    model_config = SettingsConfigDict(
        env_file=_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )


settings = Settings()

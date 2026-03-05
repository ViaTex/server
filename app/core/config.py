import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "DishaSetu API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # DATABASE
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dishasetu"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # CLOUDINARY
    CLOUDINARY_CLOUD_NAME: str = "dtcqgzamm"
    CLOUDINARY_API_KEY: str = "968996174457293"
    CLOUDINARY_API_SECRET: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()

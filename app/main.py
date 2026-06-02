from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.core.redis import get_redis_client
from app.api.v1.api import api_router
from sqlalchemy import text
from app.models.job_application import JobApplication
from app.models.user import (
    PasswordResetOTP,
    PasswordResetToken,
    EmailVerificationToken,
    PasswordHistory,
    AuthAuditLog,
    UserSession,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    origins = [str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS]
    print(f"INFO:     CORS enabled for origins: {origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def check_dependencies() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("INFO:     Database connection OK")

        # Local/dev safety net so the new apply flow works even if Alembic
        # has not been run yet for just this table.
        JobApplication.__table__.create(bind=engine, checkfirst=True)
        PasswordResetOTP.__table__.create(bind=engine, checkfirst=True)
        PasswordResetToken.__table__.create(bind=engine, checkfirst=True)
        EmailVerificationToken.__table__.create(bind=engine, checkfirst=True)
        PasswordHistory.__table__.create(bind=engine, checkfirst=True)
        AuthAuditLog.__table__.create(bind=engine, checkfirst=True)
        UserSession.__table__.create(bind=engine, checkfirst=True)

        # Backward-compatible schema patching for existing deployments.
        # Ensures newly added auth recovery columns exist even when old tables already exist.
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE password_reset_otps ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE password_reset_otps ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 5"))
            conn.execute(text("ALTER TABLE password_reset_otps ADD COLUMN IF NOT EXISTS resend_count INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE password_reset_otps ADD COLUMN IF NOT EXISTS next_resend_at TIMESTAMPTZ NULL"))

            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS device_fingerprint VARCHAR(255)"))
            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS device_label VARCHAR(255)"))
            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS login_location VARCHAR(255)"))
            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS trusted_device BOOLEAN NOT NULL DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ NULL"))
            conn.execute(text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS revoked_reason VARCHAR(255)"))
        print("INFO:     job_applications table ready")

        # Ensure profile_picture_url columns exist
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE students ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(1000)"))
            connection.execute(text("ALTER TABLE mentors ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(1000)"))
            connection.execute(text("ALTER TABLE corporates ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(1000)"))
            connection.execute(text("ALTER TABLE colleges ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(1000)"))
            connection.execute(text("ALTER TABLE admins ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(1000)"))
        print("INFO:     profile_picture_url columns verified/added for all user tables")
    except Exception as exc:
        print(f"ERROR:    Database connection failed: {exc}")

    try:
        redis_client = get_redis_client()
        redis_client.ping()
        print("INFO:     Redis connection OK")
    except Exception as exc:
        print(f"ERROR:    Redis connection failed: {exc}")

@app.get("/")
def root():
    return {"message": "Welcome to DishaSetu API"}

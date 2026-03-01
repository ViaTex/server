from typing import AsyncGenerator
import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Parse DATABASE_URL and remove sslmode parameter (not compatible with asyncpg)
def get_database_url() -> str:
    """Convert DATABASE_URL to asyncpg compatible format"""
    url = settings.DATABASE_URL
    # Remove sslmode query parameter if present (asyncpg uses connect_args instead)
    if "?sslmode=" in url:
        url = url.split("?sslmode=")[0]
    elif "&sslmode=" in url:
        url = url.replace("&sslmode=require", "").replace("&sslmode=disable", "")
    return url


def get_ssl_config():
    """Get SSL configuration for asyncpg"""
    if "sslmode=require" in settings.DATABASE_URL:
        # Create SSL context for secure connection
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    return None


# Create async engine
engine = create_async_engine(
    get_database_url(),
    echo=settings.LOG_SQL_QUERIES,  # Controlled by LOG_SQL_QUERIES setting (default: False for security)
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    connect_args={
        "ssl": get_ssl_config(),
        "server_settings": {
            "application_name": settings.APP_NAME
        }
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base class for models
class Base(DeclarativeBase):
    pass


# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

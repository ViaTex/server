from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from app.core.redis import get_redis_client
from app.api.v1.api import api_router
from sqlalchemy import text

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

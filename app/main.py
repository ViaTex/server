from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from ai.router import router as ai_router

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
app.include_router(ai_router)
app.include_router(ai_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to DishaSetu API"}

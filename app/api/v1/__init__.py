"""API v1 router"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, oauth, jobs_example

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["OAuth"])
api_router.include_router(jobs_example.router, tags=["Jobs Example (RBAC Demo)"])

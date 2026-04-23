from fastapi import APIRouter
from app.api.v1.endpoints import auth, exams, student, jobs, corporate, mentor

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(student.router, prefix="/student", tags=["student"])
api_router.include_router(mentor.router, prefix="/mentor", tags=["mentor"])
api_router.include_router(corporate.router, prefix="/corporate", tags=["corporate"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

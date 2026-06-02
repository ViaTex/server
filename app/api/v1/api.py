from fastapi import APIRouter
from app.api.v1.endpoints import auth, exams, student, jobs, corporate, mentor, admin_users, college
from app.api.v1.endpoints import auth, exams, student, jobs, corporate, mentor, admin_users
from app.api.v1.endpoints import projects, interviews, college

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(student.router, prefix="/student", tags=["student"])
api_router.include_router(mentor.router, prefix="/mentor", tags=["mentor"])
api_router.include_router(corporate.router, prefix="/corporate", tags=["corporate"])
api_router.include_router(college.router, prefix="/college", tags=["college"])
api_router.include_router(exams.router, prefix="/exams", tags=["exams"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(college.router, prefix="/college", tags=["college"])

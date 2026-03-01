"""
Example API endpoints demonstrating Role-Based Access Control (RBAC)

This module shows how to implement protected endpoints with role-based authorization
for a job posting and application management system.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user, RoleChecker
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["Jobs (Example)"])

# Role checkers
allow_hr = RoleChecker(["Corporate HR"])
allow_tpo = RoleChecker(["TPO"])
allow_staff = RoleChecker(["TPO", "Corporate HR", "Mentor"])
allow_student = RoleChecker(["Student"])


# ============= Pydantic Schemas =============

class JobCreate(BaseModel):
    """Schema for creating a job posting"""
    title: str
    company: str
    description: str
    requirements: List[str]
    salary_range: Optional[str] = None
    location: str
    job_type: str  # Full-time, Part-time, Internship


class JobResponse(BaseModel):
    """Schema for job response"""
    id: str
    title: str
    company: str
    description: str
    requirements: List[str]
    salary_range: Optional[str]
    location: str
    job_type: str
    posted_by: str
    posted_by_role: str
    created_at: datetime
    status: str  # active, closed


class ApplicationCreate(BaseModel):
    """Schema for job application"""
    job_id: str
    cover_letter: str
    resume_url: str


class ApplicationResponse(BaseModel):
    """Schema for application response"""
    id: str
    job_id: str
    student_id: str
    student_email: str
    cover_letter: str
    resume_url: str
    status: str  # pending, approved, rejected
    applied_at: datetime


# ============= Job Management Endpoints =============

@router.post(
    "/create",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(allow_hr)]
)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new job posting.
    
    **Required Role**: Corporate HR
    
    Only Corporate HR users can create job postings.
    """
    # In a real application, you would save this to the database
    # For demonstration, we'll return a mock response
    
    job_response = JobResponse(
        id="job-12345",
        title=job_data.title,
        company=job_data.company,
        description=job_data.description,
        requirements=job_data.requirements,
        salary_range=job_data.salary_range,
        location=job_data.location,
        job_type=job_data.job_type,
        posted_by=str(current_user.id),
        posted_by_role=current_user.role,
        created_at=datetime.utcnow(),
        status="active"
    )
    
    return job_response


@router.get("/list", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[str] = "active",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all job postings.
    
    **Available to**: All authenticated users
    
    Students can view to apply, Staff can view to manage.
    """
    # Mock response
    jobs = [
        JobResponse(
            id="job-001",
            title="Software Engineer",
            company="Tech Corp",
            description="Exciting opportunity for a software engineer...",
            requirements=["Python", "FastAPI", "PostgreSQL"],
            salary_range="$80,000 - $120,000",
            location="Remote",
            job_type="Full-time",
            posted_by="hr-user-id",
            posted_by_role="Corporate HR",
            created_at=datetime.utcnow(),
            status="active"
        ),
        JobResponse(
            id="job-002",
            title="Data Science Intern",
            company="Analytics Inc",
            description="Internship for data science students...",
            requirements=["Python", "Machine Learning", "Statistics"],
            salary_range="$20/hour",
            location="New York",
            job_type="Internship",
            posted_by="hr-user-id-2",
            posted_by_role="Corporate HR",
            created_at=datetime.utcnow(),
            status="active"
        )
    ]
    
    return jobs


@router.put(
    "/{job_id}/close",
    dependencies=[Depends(allow_hr)]
)
async def close_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Close a job posting.
    
    **Required Role**: Corporate HR
    
    Only the HR who posted the job can close it.
    """
    return {
        "message": f"Job {job_id} closed successfully",
        "closed_by": current_user.email
    }


# ============= Application Management Endpoints =============

@router.post(
    "/apply",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(allow_student)]
)
async def apply_to_job(
    application: ApplicationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply to a job posting.
    
    **Required Role**: Student
    
    Only students can apply to jobs.
    """
    # Mock response
    app_response = ApplicationResponse(
        id="app-12345",
        job_id=application.job_id,
        student_id=str(current_user.id),
        student_email=current_user.email,
        cover_letter=application.cover_letter,
        resume_url=application.resume_url,
        status="pending",
        applied_at=datetime.utcnow()
    )
    
    return app_response


@router.get(
    "/applications",
    response_model=List[ApplicationResponse],
    dependencies=[Depends(allow_staff)]
)
async def view_applications(
    job_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    View job applications.
    
    **Required Roles**: TPO, Corporate HR, Mentor
    
    Staff members can view applications to manage the hiring process.
    If job_id is provided, returns applications for that specific job.
    """
    # Mock response
    applications = [
        ApplicationResponse(
            id="app-001",
            job_id=job_id or "job-001",
            student_id="student-uuid-1",
            student_email="student1@example.com",
            cover_letter="I am interested in this position...",
            resume_url="https://example.com/resume1.pdf",
            status="pending",
            applied_at=datetime.utcnow()
        ),
        ApplicationResponse(
            id="app-002",
            job_id=job_id or "job-001",
            student_id="student-uuid-2",
            student_email="student2@example.com",
            cover_letter="I have the skills required...",
            resume_url="https://example.com/resume2.pdf",
            status="approved",
            applied_at=datetime.utcnow()
        )
    ]
    
    return applications


@router.put(
    "/applications/{application_id}/status",
    dependencies=[Depends(allow_staff)]
)
async def update_application_status(
    application_id: str,
    new_status: str,  # pending, approved, rejected
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update application status.
    
    **Required Roles**: TPO, Corporate HR, Mentor
    
    Staff can approve or reject applications.
    """
    if new_status not in ["pending", "approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: pending, approved, or rejected"
        )
    
    return {
        "message": f"Application {application_id} status updated to {new_status}",
        "updated_by": current_user.email,
        "updated_by_role": current_user.role
    }


@router.get(
    "/my-applications",
    response_model=List[ApplicationResponse],
    dependencies=[Depends(allow_student)]
)
async def my_applications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    View my job applications.
    
    **Required Role**: Student
    
    Students can view their own application history.
    """
    # Mock response
    applications = [
        ApplicationResponse(
            id="app-001",
            job_id="job-001",
            student_id=str(current_user.id),
            student_email=current_user.email,
            cover_letter="I am interested in this position...",
            resume_url="https://example.com/resume.pdf",
            status="pending",
            applied_at=datetime.utcnow()
        )
    ]
    
    return applications


# ============= Analytics Endpoints =============

@router.get(
    "/analytics/overview",
    dependencies=[Depends(allow_tpo)]
)
async def job_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    View job placement analytics.
    
    **Required Role**: TPO
    
    TPO can view overall placement statistics and metrics.
    """
    return {
        "total_jobs": 50,
        "active_jobs": 35,
        "total_applications": 250,
        "pending_applications": 100,
        "approved_applications": 120,
        "rejected_applications": 30,
        "placement_rate": "48%",
        "average_salary": "$95,000"
    }

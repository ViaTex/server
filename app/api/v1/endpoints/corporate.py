from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_corporate
from app.models.job import Job
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.user import Corporate
from app.models.user import Student
from app.schemas.application import JobApplicationResponse, JobApplicationUpdateRequest
from app.schemas.corporate import CorporateProfileResponse, CorporateProfileUpdate

router = APIRouter()


def _is_missing_job_applications_table(error: Exception) -> bool:
    if not isinstance(error, ProgrammingError):
        return False
    message = str(getattr(error, "orig", error)).lower()
    return 'relation "job_applications" does not exist' in message


@router.get("/profile", response_model=CorporateProfileResponse)
async def get_corporate_profile(
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate = db.query(Corporate).filter(Corporate.id == UUID(str(current_user["user_id"]))).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")
    return CorporateProfileResponse(
        id=str(corporate.id),
        email=corporate.email,
        name=corporate.name,
        bio=corporate.description,
        company_name=corporate.company_name,
        phone=corporate.phone,
        contact_person=corporate.contact_person,
        contact_designation=corporate.contact_designation,
        website_url=corporate.website_url,
        industry=corporate.industry,
        company_size=corporate.company_size,
        founded_year=corporate.founded_year,
        company_type=corporate.company_type,
        description=corporate.description,
        address=corporate.address,
    )


@router.patch("/profile", response_model=CorporateProfileResponse)
async def update_corporate_profile(
    payload: CorporateProfileUpdate,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate = db.query(Corporate).filter(Corporate.id == UUID(str(current_user["user_id"]))).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "bio":
            corporate.description = value
        else:
            setattr(corporate, key, value)

    db.commit()
    db.refresh(corporate)
    return CorporateProfileResponse(
        id=str(corporate.id),
        email=corporate.email,
        name=corporate.name,
        bio=corporate.description,
        company_name=corporate.company_name,
        phone=corporate.phone,
        contact_person=corporate.contact_person,
        contact_designation=corporate.contact_designation,
        website_url=corporate.website_url,
        industry=corporate.industry,
        company_size=corporate.company_size,
        founded_year=corporate.founded_year,
        company_type=corporate.company_type,
        description=corporate.description,
        address=corporate.address,
    )


@router.get("/applicants", response_model=list[JobApplicationResponse])
async def list_corporate_applicants(
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate_id = UUID(str(current_user["user_id"]))
    corporate = db.query(Corporate).filter(Corporate.id == corporate_id).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    try:
        applications = (
            db.query(JobApplication, Student, Job)
            .join(Student, Student.id == JobApplication.student_id)
            .join(Job, Job.id == JobApplication.job_id)
            .filter(JobApplication.corporate_id == corporate_id)
            .order_by(JobApplication.created_at.desc())
            .all()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_job_applications_table(exc):
            return []
        raise

    response: list[JobApplicationResponse] = []
    for application, student, job in applications:
        response.append(
            JobApplicationResponse(
                id=application.id,
                job_id=application.job_id,
                student_id=application.student_id,
                corporate_id=application.corporate_id,
                college_id=application.college_id,
                status=application.status.value if hasattr(application.status, "value") else str(application.status),
                expected_salary=application.expected_salary,
                cover_letter=application.cover_letter,
                resume_url=application.resume_url,
                created_at=application.created_at,
                updated_at=application.updated_at,
                student_name=student.name,
                student_email=student.email,
                student_phone=student.phone,
                job_title=job.title,
                company_name=job.company_name or corporate.company_name,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
            )
        )

    return response


@router.patch("/applicants/{application_id}", response_model=JobApplicationResponse)
async def update_corporate_applicant(
    application_id: UUID,
    payload: JobApplicationUpdateRequest,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate_id = UUID(str(current_user["user_id"]))
    corporate = db.query(Corporate).filter(Corporate.id == corporate_id).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    try:
        application_row = (
            db.query(JobApplication, Student, Job)
            .join(Student, Student.id == JobApplication.student_id)
            .join(Job, Job.id == JobApplication.job_id)
            .filter(JobApplication.id == application_id, JobApplication.corporate_id == corporate_id)
            .first()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_job_applications_table(exc):
            raise HTTPException(status_code=503, detail="Job applications are not ready yet.")
        raise

    if not application_row:
        raise HTTPException(status_code=404, detail="Application not found")

    application, student, job = application_row

    allowed_statuses = {item.value for item in ApplicationStatus}
    normalized_status = payload.status.strip().lower()
    if normalized_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid application status")

    application.status = ApplicationStatus(normalized_status)
    db.commit()
    db.refresh(application)

    return JobApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        student_id=application.student_id,
        corporate_id=application.corporate_id,
        college_id=application.college_id,
        status=application.status.value if hasattr(application.status, "value") else str(application.status),
        expected_salary=application.expected_salary,
        cover_letter=application.cover_letter,
        resume_url=application.resume_url,
        created_at=application.created_at,
        updated_at=application.updated_at,
        student_name=student.name,
        student_email=student.email,
        student_phone=student.phone,
        job_title=job.title,
        company_name=job.company_name or corporate.company_name,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
    )

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, load_only

from app.core.database import get_db
from app.core.security import get_current_corporate
from app.models.job import Job
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.user import Corporate
from app.models.user import Student
from app.schemas.application import JobApplicationResponse, JobApplicationUpdateRequest
from app.schemas.corporate import CorporateProfileResponse, CorporateProfileUpdate
from app.services.cloudinary_service import CloudinaryService

router = APIRouter()


def _is_missing_job_applications_table(error: Exception) -> bool:
    if not isinstance(error, ProgrammingError):
        return False
    message = str(getattr(error, "orig", error)).lower()
    return 'relation "job_applications" does not exist' in message


def _has_offer_letter_columns(db: Session) -> bool:
    inspector = sqlalchemy_inspect(db.bind)
    if not inspector.has_table("job_applications"):
        return False
    columns = {column["name"] for column in inspector.get_columns("job_applications")}
    return {"offer_letter", "offer_letter_sent_at"}.issubset(columns)


def _application_load_options(include_offer_letter: bool):
    columns = [
        JobApplication.id,
        JobApplication.job_id,
        JobApplication.student_id,
        JobApplication.corporate_id,
        JobApplication.college_id,
        JobApplication.status,
        JobApplication.expected_salary,
        JobApplication.cover_letter,
        JobApplication.resume_url,
        JobApplication.created_at,
        JobApplication.updated_at,
    ]
    if include_offer_letter:
        columns.extend([JobApplication.offer_letter, JobApplication.offer_letter_sent_at])
    return load_only(*columns)


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

    has_offer_letter_columns = _has_offer_letter_columns(db)

    try:
        applications = (
            db.query(JobApplication, Student, Job)
            .options(_application_load_options(has_offer_letter_columns))
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
                offer_letter=application.offer_letter if has_offer_letter_columns else None,
                offer_letter_sent_at=application.offer_letter_sent_at if has_offer_letter_columns else None,
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

    has_offer_letter_columns = _has_offer_letter_columns(db)

    try:
        application_row = (
            db.query(JobApplication, Student, Job)
            .options(_application_load_options(has_offer_letter_columns))
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

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Provide an application update")

    if payload.status is not None:
        allowed_statuses = {item.value for item in ApplicationStatus}
        normalized_status = payload.status.strip().lower()
        if normalized_status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid application status")
        application.status = ApplicationStatus(normalized_status)

    if "offer_letter" in update_data:
        if not has_offer_letter_columns:
            raise HTTPException(status_code=503, detail="Run the latest database migration before sending offer letters.")
        normalized_offer_letter = (payload.offer_letter or "").strip()
        if not normalized_offer_letter:
            raise HTTPException(status_code=400, detail="Offer letter cannot be empty")
        application.offer_letter = normalized_offer_letter
        application.offer_letter_sent_at = datetime.now(timezone.utc)

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
        offer_letter=application.offer_letter if has_offer_letter_columns else None,
        offer_letter_sent_at=application.offer_letter_sent_at if has_offer_letter_columns else None,
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


@router.post("/applicants/{application_id}/offer-letter", response_model=JobApplicationResponse)
async def upload_offer_letter(
    application_id: UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate_id = UUID(str(current_user["user_id"]))
    corporate = db.query(Corporate).filter(Corporate.id == corporate_id).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    has_offer_letter_columns = _has_offer_letter_columns(db)
    if not has_offer_letter_columns:
        raise HTTPException(status_code=503, detail="Run the latest database migration before sending offer letters.")

    filename = file.filename or "offer-letter.pdf"
    content_type = (file.content_type or "").lower()
    if not (filename.lower().endswith(".pdf") or content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only PDF offer letters are supported")

    content = await file.read()
    max_size = 5 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="Offer letter PDF must be 5MB or smaller")

    try:
        application_row = (
            db.query(JobApplication, Student, Job)
            .options(_application_load_options(True))
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

    try:
        offer_letter_url = CloudinaryService.upload_media_bytes(
            content,
            folder="offer_letters",
            filename=filename,
            resource_type="auto",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload offer letter: {exc}") from exc

    application.offer_letter = offer_letter_url
    application.offer_letter_sent_at = datetime.now(timezone.utc)
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
        offer_letter=application.offer_letter,
        offer_letter_sent_at=application.offer_letter_sent_at,
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

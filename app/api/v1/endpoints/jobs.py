from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, load_only

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.job import Job, JobStatus, JobType
from app.models.user import Student
from app.schemas.application import JobApplicationCreateRequest, JobApplicationResponse
from app.schemas.job import JobCreateRequest, JobResponse

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


def _serialize_job(job: Job) -> dict:
    return {
        "id": str(job.id),
        "title": job.title,
        "description": job.description,
        "requirements": job.requirements,
        "responsibilities": job.responsibilities,
        "job_type": job.job_type.value if hasattr(job.job_type, "value") else str(job.job_type),
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "location": job.location,
        "remote_work": job.remote_work,
        "travel_required": job.travel_required,
        "mode_of_work": job.mode_of_work,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "ctc_with_probation": job.ctc_with_probation,
        "ctc_after_probation": job.ctc_after_probation,
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
        "education_level": job.education_level,
        "education_degree": job.education_degree,
        "education_branch": job.education_branch,
        "skills_required": job.skills_required,
        "certifications_required": job.certifications_required,
        "application_deadline": job.application_deadline,
        "max_applications": job.max_applications,
        "current_applications": job.current_applications,
        "industry": job.industry,
        "joining_location": job.joining_location,
        "selection_process": job.selection_process,
        "campus_drive_date": job.campus_drive_date,
        "service_agreement_details": job.service_agreement_details,
        "number_of_openings": job.number_of_openings,
        "expiration_date": job.expiration_date,
        "perks_and_benefits": job.perks_and_benefits,
        "eligibility_criteria": job.eligibility_criteria,
        "views_count": job.views_count,
        "applications_count": job.applications_count,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "published_at": job.published_at,
        "corporate_id": str(job.corporate_id) if job.corporate_id else None,
        "college_id": str(job.college_id) if job.college_id else None,
        "is_active": job.is_active,
        "can_apply": job.can_apply,
        "company_name": job.company_name,
        "company_logo": job.company_logo,
        "company_website": job.company_website,
        "company_address": job.company_address,
        "company_size": job.company_size,
        "company_type": job.company_type,
        "company_founded": job.company_founded,
        "company_description": job.company_description,
        "contact_person": job.contact_person,
        "contact_designation": job.contact_designation,
        "is_public": job.is_public,
        "public_link_token": job.public_link_token,
        "min_des_score": job.min_des_score,
        "max_des_score": job.max_des_score,
        "ongoing_project_title": job.ongoing_project_title,
        "ongoing_project_description": job.ongoing_project_description,
    }


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] not in {"corporate", "college"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only corporate or college can create jobs")

    try:
        owner_id = UUID(str(current_user["user_id"]))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    payload_data = payload.model_dump(exclude={"job_type"})
    job = Job(
        **payload_data,
        job_type=JobType(payload.job_type),
        status=JobStatus.ACTIVE,
        is_public=True,
        published_at=datetime.now(timezone.utc),
    )

    if current_user["user_type"] == "corporate":
        job.corporate_id = owner_id
    else:
        job.college_id = owner_id

    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.post("/{job_id}/apply", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: UUID,
    payload: JobApplicationCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can apply to jobs")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.can_apply:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This job is not accepting applications")

    student = db.query(Student).filter(Student.id == UUID(str(current_user["user_id"]))).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    if not student.resume_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload your resume before applying")

    try:
        existing_application = (
            db.query(JobApplication)
            .filter(JobApplication.job_id == job.id, JobApplication.student_id == student.id)
            .first()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_job_applications_table(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Job applications are not ready yet. Run the latest database migration and try again.",
            )
        raise
    if existing_application:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already applied to this job")

    application = JobApplication(
        job_id=job.id,
        student_id=student.id,
        corporate_id=job.corporate_id,
        college_id=job.college_id,
        status=ApplicationStatus.APPLIED,
        expected_salary=payload.expected_salary,
        cover_letter=payload.cover_letter,
        resume_url=student.resume_url,
    )
    job.current_applications = (job.current_applications or 0) + 1
    job.applications_count = (job.applications_count or 0) + 1

    try:
        db.add(application)
        db.commit()
        db.refresh(application)
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_job_applications_table(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Job applications are not ready yet. Run the latest database migration and try again.",
            )
        raise

    has_offer_letter_columns = _has_offer_letter_columns(db)

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
        company_name=job.company_name,
    )


@router.get("/applications/me", response_model=list[JobApplicationResponse])
async def list_my_applications(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can view their applications")

    try:
        has_offer_letter_columns = _has_offer_letter_columns(db)
        applications = (
            db.query(JobApplication, Job)
            .options(_application_load_options(has_offer_letter_columns))
            .join(Job, Job.id == JobApplication.job_id)
            .filter(JobApplication.student_id == UUID(str(current_user["user_id"])))
            .order_by(JobApplication.created_at.desc())
            .all()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_job_applications_table(exc):
            return []
        raise

    response: list[JobApplicationResponse] = []
    for application, job in applications:
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
                job_title=job.title,
                company_name=job.company_name,
            )
        )

    return response


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    mine: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Job).order_by(Job.created_at.desc())

    if current_user["user_type"] == "student":
        query = query.filter(Job.status == JobStatus.ACTIVE)

    if mine:
        if current_user["user_type"] not in {"corporate", "college"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only corporate or college can view own jobs")
        try:
            owner_id = UUID(str(current_user["user_id"]))
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

        if current_user["user_type"] == "corporate":
            query = query.filter(Job.corporate_id == owner_id)
        else:
            query = query.filter(Job.college_id == owner_id)

    jobs = query.all()
    return [_serialize_job(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _serialize_job(job)

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    payload: JobCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] not in {"corporate", "college"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only corporate or college can update jobs")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    try:
        owner_id = UUID(str(current_user["user_id"]))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    if current_user["user_type"] == "corporate" and job.corporate_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this job")
    elif current_user["user_type"] == "college" and job.college_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this job")
        
    payload_data = payload.model_dump(exclude={"job_type"})
    for key, value in payload_data.items():
        setattr(job, key, value)
    
    job.job_type = JobType(payload.job_type)
    
    db.commit()
    db.refresh(job)
    return _serialize_job(job)

@router.patch("/{job_id}/approve", response_model=JobResponse)
async def approve_job(
    job_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.get("user_type") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can approve jobs")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.is_public = True
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


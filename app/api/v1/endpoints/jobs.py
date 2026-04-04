from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.job import Job, JobStatus, JobType
from app.schemas.job import JobCreateRequest, JobResponse

router = APIRouter()


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
    )

    if current_user["user_type"] == "corporate":
        job.corporate_id = owner_id
    else:
        job.college_id = owner_id

    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    mine: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Job).order_by(Job.created_at.desc())

    if current_user["user_type"] == "student":
        query = query.filter(Job.is_public == True)

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


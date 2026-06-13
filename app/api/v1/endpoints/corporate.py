from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID


# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, Request
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import ProgrammingError
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, load_only

from app.core.database import get_db
from app.core.security import get_current_corporate
from app.models.job import Job
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.resume_status import ResumeStatus
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
    return True


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


def _application_response(
    application: JobApplication,
    student: Student,
    job: Job,
    corporate: Corporate,
    has_offer_letter_columns: bool,
    resume_status: ResumeStatus | None = None,
) -> JobApplicationResponse:
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
        student_technical_skills=student.technical_skills,
        student_des_score=student.current_des_score,
        student_ats_score=resume_status.ats_score if resume_status else None,
        job_title=job.title,
        company_name=job.company_name or corporate.company_name,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
    )


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
    request: Request,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    print("DEBUG HEADERS:", request.headers)
    corporate_id = UUID(str(current_user["user_id"]))
    corporate = db.query(Corporate).filter(Corporate.id == corporate_id).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    has_offer_letter_columns = _has_offer_letter_columns(db)

    try:
        applications = (
            db.query(JobApplication, Student, Job, ResumeStatus)
            .options(_application_load_options(has_offer_letter_columns))
            .join(Student, Student.id == JobApplication.student_id)
            .join(Job, Job.id == JobApplication.job_id)
            .outerjoin(ResumeStatus, ResumeStatus.student_id == Student.id)
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
    for application, student, job, resume_status in applications:
        response.append(_application_response(application, student, job, corporate, has_offer_letter_columns, resume_status))

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
            db.query(JobApplication, Student, Job, ResumeStatus)
            .options(_application_load_options(has_offer_letter_columns))
            .join(Student, Student.id == JobApplication.student_id)
            .join(Job, Job.id == JobApplication.job_id)
            .outerjoin(ResumeStatus, ResumeStatus.student_id == Student.id)
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

    application, student, job, resume_status = application_row

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Provide an application update")

    if payload.status is not None:
        allowed_statuses = {item.value for item in ApplicationStatus}
        normalized_status = payload.status.strip().lower()
        if normalized_status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid application status")
        application.status = ApplicationStatus(normalized_status)

        # Placement tracking: auto-stamp when moving to 'selected'
        if normalized_status == ApplicationStatus.SELECTED.value:
            application.placed_at = datetime.now(timezone.utc)
            application.placed_by_corporate_name = corporate.company_name
            application.placed_job_title = job.title

    if "cover_letter" in update_data:
        application.cover_letter = payload.cover_letter

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

    return _application_response(application, student, job, corporate, has_offer_letter_columns, resume_status)


@router.delete("/applicants/{application_id}")
async def delete_corporate_applicant(
    application_id: UUID,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate_id = UUID(str(current_user["user_id"]))
    corporate = db.query(Corporate).filter(Corporate.id == corporate_id).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    try:
        application = (
            db.query(JobApplication)
            .filter(JobApplication.id == application_id, JobApplication.corporate_id == corporate_id)
            .first()
        )
    except ProgrammingError as exc:
        db.rollback()
        if _is_missing_job_applications_table(exc):
            raise HTTPException(status_code=503, detail="Job applications are not ready yet.")
        raise

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job:
        job.current_applications = max((job.current_applications or 0) - 1, 0)
        job.applications_count = max((job.applications_count or 0) - 1, 0)

    db.delete(application)
    db.commit()

    return {"message": "Application removed", "id": str(application_id)}


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
            db.query(JobApplication, Student, Job, ResumeStatus)
            .options(_application_load_options(True))
            .join(Student, Student.id == JobApplication.student_id)
            .join(Job, Job.id == JobApplication.job_id)
            .outerjoin(ResumeStatus, ResumeStatus.student_id == Student.id)
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

    application, student, job, resume_status = application_row

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

    return _application_response(application, student, job, corporate, True, resume_status)


# ════════════════════════════════════════════════════════════════════════════
# SMART MATCH  —  Phase 2 of the Trust-Based Hiring Pipeline
# ════════════════════════════════════════════════════════════════════════════

from app.models.user import SkillEvaluation, SkillEvaluationStatus, SkillEvaluationVerdict, Mentor
from app.models.project import Project


@router.get("/smart-matches")
async def smart_matches(
    min_des: float = Query(75.0, ge=0, le=100, description="Minimum DES score filter"),
    skills: list[str] = Query(default=[], description="Required verified skill domains"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    """
    Phase 2 — Zero-Screening Smart Match.
    Returns verified students whose DES score meets the threshold
    and have at least one successfully evaluated SkillEvaluation.
    Reads Student.current_des_score directly — no recomputation.
    """
    # Base: students with sufficient DES
    query = (
        db.query(Student)
        .filter(Student.current_des_score >= min_des)
        .order_by(Student.current_des_score.desc())
    )

    students: list[Student] = query.all()

    # Only include students with at least one PASSING evaluated viva
    passing_verdicts = {
        SkillEvaluationVerdict.EXCELLENT,
        SkillEvaluationVerdict.VERY_GOOD,
        SkillEvaluationVerdict.GOOD,
    }

    results = []
    for student in students:
        evals = (
            db.query(SkillEvaluation)
            .filter(
                SkillEvaluation.student_id == student.id,
                SkillEvaluation.status == SkillEvaluationStatus.EVALUATED,
                SkillEvaluation.verdict.in_(list(passing_verdicts)),
            )
            .all()
        )
        if not evals:
            continue

        # Collect verified skill domains from linked projects
        verified_skill_domains: list[str] = []
        for e in evals:
            if e.project_id:
                proj = db.query(Project).filter(Project.id == e.project_id).first()
                if proj and proj.skill_domain and proj.skill_domain not in verified_skill_domains:
                    verified_skill_domains.append(proj.skill_domain)

        # Skill filter: if caller specified required skills, at least one must match
        if skills:
            matched = any(
                any(req.lower() in dom.lower() for dom in verified_skill_domains)
                for req in skills
            )
            if not matched:
                continue

        # Best evaluation for summary
        best_eval = max(evals, key=lambda e: (e.total_score or 0))
        mentor = db.query(Mentor).filter(Mentor.id == best_eval.mentor_id).first()

        results.append({
            "student_id": str(student.id),
            "name": student.name,
            "email": student.email,
            "location": student.city or student.state or student.country,
            "des_score": float(student.current_des_score or 0),
            "badge": student.badge,
            "verified_skills": verified_skill_domains,
            "best_viva_score": best_eval.total_score,
            "best_viva_verdict": best_eval.verdict.value if best_eval.verdict else None,
            "mentor_name": mentor.name if mentor else None,
            "github_profile": student.github_profile,
            "linkedin_profile": student.linkedin_profile,
        })

        if len(results) >= limit:
            break

    return results


# ════════════════════════════════════════════════════════════════════════════
# CANDIDATE DETAIL  —  Phase 3: Full profile + Mentor Evaluation Report
# ════════════════════════════════════════════════════════════════════════════

@router.get("/candidates/{student_id}")
async def get_candidate_detail(
    student_id: str,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    """
    Phase 3 — Shortlisting with Trust.
    Returns the full candidate profile including mentor evaluation reports,
    DES score, verified projects, and professional links.
    """
    try:
        sid = UUID(student_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid student_id")

    student = db.query(Student).filter(Student.id == sid).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # All evaluated skill evaluations
    evals = (
        db.query(SkillEvaluation)
        .filter(
            SkillEvaluation.student_id == sid,
            SkillEvaluation.status == SkillEvaluationStatus.EVALUATED,
        )
        .order_by(SkillEvaluation.updated_at.desc())
        .all()
    )

    evaluation_reports = []
    for e in evals:
        mentor = db.query(Mentor).filter(Mentor.id == e.mentor_id).first()
        project = db.query(Project).filter(Project.id == e.project_id).first() if e.project_id else None
        evaluation_reports.append({
            "evaluation_id": str(e.id),
            "mentor_name": mentor.name if mentor else None,
            "mentor_role": mentor.current_role if mentor else None,
            "project_title": project.title if project else None,
            "project_github": project.github_url if project else None,
            "skill_domain": project.skill_domain if project else None,
            "score_technical": e.score_technical,
            "score_practical": e.score_practical,
            "score_communication": e.score_communication,
            "score_originality": e.score_originality,
            "total_score": e.total_score,
            "verdict": e.verdict.value if e.verdict else None,
            "feedback_strengths": e.feedback_strengths,
            "feedback_improvements": e.feedback_improvements,
            "evaluated_at": e.updated_at or e.created_at,
        })

    # Verified projects
    from app.models.project import ProjectStatus
    projects = (
        db.query(Project)
        .filter(Project.student_id == sid, Project.status == ProjectStatus.VERIFIED)
        .all()
    )

    return {
        "student_id": str(student.id),
        "name": student.name,
        "email": student.email,
        "phone": student.phone,
        "bio": student.bio,
        "location": f"{student.city or ''}, {student.state or ''}, {student.country or ''}".strip(", "),
        "des_score": float(student.current_des_score or 0),
        "badge": student.badge,
        "technical_skills": student.technical_skills,
        "soft_skills": student.soft_skills,
        "education": student.education or [],
        "github_profile": student.github_profile,
        "linkedin_profile": student.linkedin_profile,
        "personal_website": student.personal_website,
        "profile_picture_url": student.profile_picture_url,
        "evaluation_reports": evaluation_reports,
        "verified_projects": [
            {
                "id": str(p.id),
                "title": p.title,
                "skill_domain": p.skill_domain,
                "tech_stack": p.tech_stack or [],
                "github_url": p.github_url,
                "live_url": p.live_url,
                "verified_badge": p.verified_badge,
            }
            for p in projects
        ],
    }

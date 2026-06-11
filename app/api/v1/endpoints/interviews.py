from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_corporate, get_current_student, get_current_user
from app.models.interview import Interview, InterviewStatus
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.project import Project
from app.models.user import Corporate, Mentor, SkillEvaluation, SkillEvaluationStatus, SkillEvaluationVerdict, Student
from app.schemas.interview import InterviewComplete, InterviewConfirm, InterviewCreate, InterviewResponse, VerifiedSkillResponse

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_slots(raw: list) -> list[datetime]:
    parsed = []
    for v in raw or []:
        if isinstance(v, datetime):
            parsed.append(v)
        elif isinstance(v, str):
            try:
                parsed.append(datetime.fromisoformat(v.replace("Z", "+00:00")))
            except ValueError:
                pass
    return parsed


def _get_verified_skills(db: Session, student_id: UUID) -> list[str]:
    """Return list of skill domains verified by a mentor for this student."""
    evals = (
        db.query(SkillEvaluation)
        .filter(
            SkillEvaluation.student_id == student_id,
            SkillEvaluation.status == SkillEvaluationStatus.EVALUATED,
            SkillEvaluation.verdict.in_(
                [SkillEvaluationVerdict.EXCELLENT, SkillEvaluationVerdict.VERY_GOOD, SkillEvaluationVerdict.GOOD]
            ),
        )
        .all()
    )
    skills: list[str] = []
    for e in evals:
        if e.project_id:
            from app.models.project import Project
            proj = db.query(Project).filter(Project.id == e.project_id).first()
            if proj and proj.skill_domain and proj.skill_domain not in skills:
                skills.append(proj.skill_domain)
    return skills


def _serialize(
    interview: Interview,
    db: Session,
) -> InterviewResponse:
    student = db.query(Student).filter(Student.id == interview.student_id).first()
    corporate = db.query(Corporate).filter(Corporate.id == interview.corporate_id).first()
    job_app = db.query(JobApplication).filter(JobApplication.id == interview.job_application_id).first()
    job = db.query(Job).filter(Job.id == job_app.job_id).first() if job_app else None

    return InterviewResponse(
        id=str(interview.id),
        job_application_id=str(interview.job_application_id),
        corporate_id=str(interview.corporate_id),
        student_id=str(interview.student_id),
        proposed_slots=_parse_slots(interview.proposed_slots),
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        meeting_link=interview.meeting_link,
        interview_type=interview.interview_type,
        status=interview.status,
        interviewer_notes=interview.interviewer_notes,
        outcome=interview.outcome,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        student_name=student.name if student else None,
        student_email=student.email if student else None,
        job_title=job.title if job else None,
        company_name=(job.company_name or corporate.company_name) if (job and corporate) else None,
        company_logo=job.company_logo if job else None,
        company_website=job.company_website if job else None,
        company_description=job.company_description if job else None,
        company_address=job.company_address if job else None,
        job_description=job.description if job else None,
        job_requirements=job.requirements if job else None,
        job_responsibilities=job.responsibilities if job else None,
        contact_person=job.contact_person if job else None,
        contact_designation=job.contact_designation if job else None,
        verified_skills=_get_verified_skills(db, interview.student_id),
    )


# ── Corporate: propose interview ─────────────────────────────────────────────

@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreate,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    """Corporate proposes interview slots for a shortlisted application."""
    corporate_id = UUID(str(current_user["user_id"]))

    try:
        app_id = UUID(payload.job_application_id)
        student_id = UUID(payload.student_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    # Verify the application belongs to this corporate
    app = db.query(JobApplication).filter(
        JobApplication.id == app_id,
        JobApplication.corporate_id == corporate_id,
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or not owned by this corporate")

    interview = Interview(
        job_application_id=app_id,
        corporate_id=corporate_id,
        student_id=student_id,
        proposed_slots=[s.isoformat() for s in payload.proposed_slots],
        duration_minutes=payload.duration_minutes,
        meeting_link=payload.meeting_link,
        interview_type=payload.interview_type,
        status=InterviewStatus.PROPOSED,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _serialize(interview, db)


# ── Student: confirm a slot ──────────────────────────────────────────────────

@router.patch("/{interview_id}/confirm", response_model=InterviewResponse)
async def confirm_interview(
    interview_id: str,
    payload: InterviewConfirm,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Student confirms one of the proposed interview slots."""
    try:
        iid = UUID(interview_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interview_id")

    interview = db.query(Interview).filter(
        Interview.id == iid,
        Interview.student_id == UUID(str(current_user["user_id"])),
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    interview.scheduled_at = payload.scheduled_at
    if payload.meeting_link:
        interview.meeting_link = payload.meeting_link
    interview.status = InterviewStatus.CONFIRMED
    db.commit()
    db.refresh(interview)
    return _serialize(interview, db)


# ── Corporate: complete + record outcome ─────────────────────────────────────

@router.patch("/{interview_id}/complete", response_model=InterviewResponse)
async def complete_interview(
    interview_id: str,
    payload: InterviewComplete,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    """Corporate marks interview as completed and records outcome + notes."""
    try:
        iid = UUID(interview_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interview_id")

    interview = db.query(Interview).filter(
        Interview.id == iid,
        Interview.corporate_id == UUID(str(current_user["user_id"])),
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    interview.status = InterviewStatus.COMPLETED
    interview.interviewer_notes = payload.interviewer_notes
    interview.outcome = payload.outcome
    db.commit()
    db.refresh(interview)
    return _serialize(interview, db)


# ── Corporate: cancel interview ──────────────────────────────────────────────

@router.patch("/{interview_id}/cancel", response_model=InterviewResponse)
async def cancel_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a scheduled interview (corporate or student can cancel)."""
    try:
        iid = UUID(interview_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interview_id")

    user_id = UUID(str(current_user["user_id"]))
    user_type = current_user["user_type"]

    interview = db.query(Interview).filter(Interview.id == iid).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if user_type == "corporate" and interview.corporate_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorised")
    if user_type == "student" and interview.student_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorised")

    interview.status = InterviewStatus.CANCELLED
    db.commit()
    db.refresh(interview)
    return _serialize(interview, db)


# ── Student: list my interviews ──────────────────────────────────────────────

@router.get("/me", response_model=list[InterviewResponse])
async def list_my_interviews(
    status: Optional[str] = Query(None, description="Filter by interview status, comma-separated"),
    search: Optional[str] = Query(None, description="Search by company or role"),
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Student lists all their upcoming and past interviews."""
    student_id = UUID(str(current_user["user_id"]))
    query = db.query(Interview).filter(Interview.student_id == student_id)

    if status:
        status_values = [s.strip() for s in status.split(',') if s.strip()]
        query = query.filter(Interview.status.in_(status_values))

    if search:
        search_term = f"%{search.lower()}%"
        query = query.join(JobApplication, JobApplication.id == Interview.job_application_id)
        query = query.join(Job, Job.id == JobApplication.job_id)
        query = query.filter(
            or_(
                func.lower(Job.title).like(search_term),
                func.lower(Job.company_name).like(search_term),
                func.lower(Job.description).like(search_term),
            )
        )

    interviews = query.order_by(Interview.created_at.desc()).all()
    return [_serialize(i, db) for i in interviews]


def _get_verified_skill_reports(db: Session, student_id: UUID) -> list[dict]:
    evaluations = (
        db.query(SkillEvaluation)
        .filter(
            SkillEvaluation.student_id == student_id,
            SkillEvaluation.status == SkillEvaluationStatus.EVALUATED,
            SkillEvaluation.verdict.in_(
                [SkillEvaluationVerdict.EXCELLENT, SkillEvaluationVerdict.VERY_GOOD, SkillEvaluationVerdict.GOOD]
            ),
        )
        .order_by(SkillEvaluation.updated_at.desc())
        .all()
    )

    reports = []
    seen_skills = set()
    for evaluation in evaluations:
        if not evaluation.project_id:
            continue
        project = db.query(Project).filter(Project.id == evaluation.project_id).first()
        mentor = db.query(Mentor).filter(Mentor.id == evaluation.mentor_id).first()
        skill_name = project.skill_domain if project and project.skill_domain else None
        if not skill_name or skill_name in seen_skills:
            continue
        seen_skills.add(skill_name)
        reports.append({
            "skill_name": skill_name,
            "total_score": evaluation.total_score,
            "verdict": evaluation.verdict.value if evaluation.verdict else None,
            "mentor_name": mentor.name if mentor else None,
            "verified_at": evaluation.updated_at or evaluation.created_at,
            "project_title": project.title if project else None,
        })
        if len(reports) >= 5:
            break
    return reports


def _get_preparation_tips(interview_type: Optional[str], job_title: Optional[str], company_name: Optional[str]) -> list[str]:
    tips = []
    if job_title:
        if 'developer' in job_title.lower() or 'engineer' in job_title.lower():
            tips.append('Review system design fundamentals and common coding principles before the interview.')
        if 'frontend' in job_title.lower() or 'react' in job_title.lower():
            tips.append('Focus on component architecture, browser rendering, and modern frontend patterns.')
        if 'backend' in job_title.lower() or 'api' in job_title.lower():
            tips.append('Brush up on API design, database modeling, and performance tuning.')
        if 'data' in job_title.lower() or 'machine learning' in job_title.lower():
            tips.append('Prepare to explain core algorithms and how you evaluate model performance.')
    if interview_type:
        if interview_type == 'technical':
            tips.append('Prepare to explain your project architecture, technical decisions, and trade-offs clearly.')
        if interview_type == 'culture_fit':
            tips.append('Be ready to discuss your strengths, collaboration style, and how you handle ambiguity.')
        if interview_type == 'hr':
            tips.append('Review your career goals, strengths, and experiences with teamwork and leadership.')
        if interview_type == 'final':
            tips.append('Summarize your impact, long-term goals, and fit for the company with confidence.')
    if company_name:
        tips.append(f'Look up {company_name} culture and products to tailor your examples to their mission.')
    if not tips:
        tips.append('Review the role, interview format, and your verified skills before the meeting.')
    return tips


@router.get('/me/verified-skills', response_model=list[VerifiedSkillResponse])
async def list_verified_skills(
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    student_id = UUID(str(current_user['user_id']))
    return _get_verified_skill_reports(db, student_id)


@router.get('/me/preparation-tips')
async def get_preparation_tips(
    interview_type: Optional[str] = Query(None),
    job_title: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return _get_preparation_tips(interview_type, job_title, company_name)


# ── Corporate: list all interviews ───────────────────────────────────────────

@router.get("/corporate/all", response_model=list[InterviewResponse])
async def list_corporate_interviews(
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    """Corporate lists all interviews they have proposed or scheduled."""
    corporate_id = UUID(str(current_user["user_id"]))
    interviews = (
        db.query(Interview)
        .filter(Interview.corporate_id == corporate_id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [_serialize(i, db) for i in interviews]

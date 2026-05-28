from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_corporate, get_current_student, get_current_user
from app.models.interview import Interview, InterviewStatus
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.user import SkillEvaluation, SkillEvaluationStatus, SkillEvaluationVerdict, Student, Corporate
from app.schemas.interview import InterviewComplete, InterviewConfirm, InterviewCreate, InterviewResponse

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
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Student lists all their upcoming and past interviews."""
    student_id = UUID(str(current_user["user_id"]))
    interviews = (
        db.query(Interview)
        .filter(Interview.student_id == student_id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [_serialize(i, db) for i in interviews]


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

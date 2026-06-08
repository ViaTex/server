from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_mentor, get_current_student
from app.models.user import Mentor, SkillEvaluation, Student
from app.schemas.mentor import (
    MentorProfileResponse,
    MentorProfileUpdate,
    SkillEvaluationCreate,
    SkillEvaluationResponse,
    SkillEvaluationScheduleUpdate,
    SkillEvaluationScoringUpdate,
    SkillEvaluationStudentReviewUpdate,
)

router = APIRouter()


def _as_datetime_list(raw_slots: list) -> list[datetime]:
    parsed_slots: list[datetime] = []
    for value in raw_slots or []:
        if isinstance(value, datetime):
            parsed_slots.append(value)
            continue
        if isinstance(value, str):
            try:
                parsed_slots.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
                continue
            except ValueError:
                pass
    return parsed_slots


def _serialize_evaluation(evaluation: SkillEvaluation) -> SkillEvaluationResponse:
    project_data = None
    if evaluation.project:
        project_data = {
            "title": evaluation.project.title,
            "description": evaluation.project.description,
            "github_url": evaluation.project.github_url,
            "live_url": evaluation.project.live_url,
            "skill_domain": evaluation.project.skill_domain,
        }
        
    student_data = None
    if evaluation.student:
        student_data = {
            "name": evaluation.student.name,
            "email": evaluation.student.email,
            "profile_picture_url": evaluation.student.profile_picture_url,
        }

    return SkillEvaluationResponse(
        evaluation_id=str(evaluation.id),
        mentor_id=str(evaluation.mentor_id),
        student_id=str(evaluation.student_id),
        project_id=str(evaluation.project_id) if evaluation.project_id else None,
        status=evaluation.status,
        proposed_slots=_as_datetime_list(evaluation.proposed_slots or []),
        confirmed_slot=evaluation.confirmed_slot,
        viva_meeting_link=evaluation.viva_meeting_link,
        score_technical=evaluation.score_technical,
        score_practical=evaluation.score_practical,
        score_communication=evaluation.score_communication,
        score_originality=evaluation.score_originality,
        total_score=evaluation.total_score,
        verdict=evaluation.verdict,
        feedback_strengths=evaluation.feedback_strengths,
        feedback_improvements=evaluation.feedback_improvements,
        student_rating_of_mentor=evaluation.student_rating_of_mentor,
        student_technical_issues=evaluation.student_technical_issues,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
        project=project_data,
        student=student_data,
    )


def _refresh_mentor_rating(db: Session, mentor_id: UUID) -> None:
    avg_rating = (
        db.query(func.avg(SkillEvaluation.student_rating_of_mentor))
        .filter(
            SkillEvaluation.mentor_id == mentor_id,
            SkillEvaluation.student_rating_of_mentor.isnot(None),
        )
        .scalar()
    )
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()
    if mentor:
        mentor.average_rating = float(avg_rating or 0.0)


@router.get("/profile", response_model=MentorProfileResponse)
async def get_mentor_profile(
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = db.query(Mentor).filter(Mentor.id == UUID(str(current_user["user_id"]))).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor profile not found")

    return MentorProfileResponse(
        id=str(mentor.id),
        user_id=str(mentor.user_id),
        email=mentor.email,
        name=mentor.name,
        profile_picture_url=mentor.profile_picture_url,
        phone=mentor.phone,
        current_role=mentor.current_role,
        expertise_areas=mentor.expertise_areas or [],
        experience_years=mentor.experience_years,
        motivation=mentor.motivation,
        average_rating=float(mentor.average_rating or 0.0),
        linkedin_profile=mentor.linkedin_profile,
        github_profile=mentor.github_profile,
        personal_website=mentor.personal_website,
    )


@router.patch("/profile", response_model=MentorProfileResponse)
async def update_mentor_profile(
    payload: MentorProfileUpdate,
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = db.query(Mentor).filter(Mentor.id == UUID(str(current_user["user_id"]))).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor profile not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(mentor, key, value)

    db.commit()
    db.refresh(mentor)

    return MentorProfileResponse(
        id=str(mentor.id),
        user_id=str(mentor.user_id),
        email=mentor.email,
        name=mentor.name,
        profile_picture_url=mentor.profile_picture_url,
        phone=mentor.phone,
        current_role=mentor.current_role,
        expertise_areas=mentor.expertise_areas or [],
        experience_years=mentor.experience_years,
        motivation=mentor.motivation,
        average_rating=float(mentor.average_rating or 0.0),
        linkedin_profile=mentor.linkedin_profile,
        github_profile=mentor.github_profile,
        personal_website=mentor.personal_website,
    )


@router.post("/evaluations", response_model=SkillEvaluationResponse)
async def create_skill_evaluation(
    payload: SkillEvaluationCreate,
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = db.query(Mentor).filter(Mentor.id == UUID(str(current_user["user_id"]))).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor profile not found")

    try:
        student_id = UUID(payload.student_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid student_id") from exc

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    project_id = None
    if payload.project_id:
        try:
            project_id = UUID(payload.project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid project_id") from exc

    evaluation = SkillEvaluation(
        mentor_id=mentor.id,
        student_id=student_id,
        project_id=project_id,
        status=payload.status,
        proposed_slots=[slot.isoformat() for slot in payload.proposed_slots],
        confirmed_slot=payload.confirmed_slot,
        viva_meeting_link=payload.viva_meeting_link,
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _serialize_evaluation(evaluation)


@router.get("/evaluations", response_model=list[SkillEvaluationResponse])
async def list_skill_evaluations(
    only_assigned_to_me: bool = Query(True),
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    query = db.query(SkillEvaluation)
    if only_assigned_to_me:
        query = query.filter(SkillEvaluation.mentor_id == UUID(str(current_user["user_id"])))

    evaluations = query.order_by(SkillEvaluation.created_at.desc()).all()
    return [_serialize_evaluation(item) for item in evaluations]


@router.patch("/evaluations/{evaluation_id}/schedule", response_model=SkillEvaluationResponse)
async def update_skill_evaluation_schedule(
    evaluation_id: str,
    payload: SkillEvaluationScheduleUpdate,
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    try:
        evaluation_uuid = UUID(evaluation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid evaluation_id") from exc

    evaluation = (
        db.query(SkillEvaluation)
        .filter(
            SkillEvaluation.id == evaluation_uuid,
            SkillEvaluation.mentor_id == UUID(str(current_user["user_id"])),
        )
        .first()
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Skill evaluation not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "proposed_slots" in update_data and update_data["proposed_slots"] is not None:
        update_data["proposed_slots"] = [slot.isoformat() for slot in update_data["proposed_slots"]]

    for key, value in update_data.items():
        setattr(evaluation, key, value)

    db.commit()
    db.refresh(evaluation)
    return _serialize_evaluation(evaluation)


@router.patch("/evaluations/{evaluation_id}/score", response_model=SkillEvaluationResponse)
async def score_skill_evaluation(
    evaluation_id: str,
    payload: SkillEvaluationScoringUpdate,
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    try:
        evaluation_uuid = UUID(evaluation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid evaluation_id") from exc

    evaluation = (
        db.query(SkillEvaluation)
        .filter(
            SkillEvaluation.id == evaluation_uuid,
            SkillEvaluation.mentor_id == UUID(str(current_user["user_id"])),
        )
        .first()
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Skill evaluation not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(evaluation, key, value)

    db.commit()
    db.refresh(evaluation)
    return _serialize_evaluation(evaluation)


@router.patch("/evaluations/{evaluation_id}/student-review", response_model=SkillEvaluationResponse)
async def submit_student_review(
    evaluation_id: str,
    payload: SkillEvaluationStudentReviewUpdate,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        evaluation_uuid = UUID(evaluation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid evaluation_id") from exc

    evaluation = (
        db.query(SkillEvaluation)
        .filter(
            SkillEvaluation.id == evaluation_uuid,
            SkillEvaluation.student_id == UUID(str(current_user["user_id"])),
        )
        .first()
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Skill evaluation not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(evaluation, key, value)

    _refresh_mentor_rating(db, evaluation.mentor_id)
    db.commit()
    db.refresh(evaluation)
    return _serialize_evaluation(evaluation)

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_mentor, get_current_student
from app.models.exam_response import ExamResponse
from app.models.exam_review_assignment import ExamReviewAssignment
from app.models.exam_session import ExamSession
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
from app.schemas.mentor_review import (
    ExamReviewAssignmentDetail,
    ExamReviewAssignmentItem,
    ExamReviewResponsePayload,
    ExamReviewStudentPayload,
    MentorExamReviewScore,
)

router = APIRouter()


def _extract_video_url(user_response: str | None) -> str | None:
    if not user_response:
        return None
    try:
        payload = json.loads(user_response)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        video_url = payload.get("video_url")
        if isinstance(video_url, str) and video_url.strip():
            return video_url
    return None


def _parse_json_or_text(raw: str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw


def _build_response_payload(response: ExamResponse) -> ExamReviewResponsePayload:
    return ExamReviewResponsePayload(
        response_id=str(response.id),
        section_type=response.section_type,
        question_text=_parse_json_or_text(response.question_text),
        user_response=_parse_json_or_text(response.user_response),
        video_url=_extract_video_url(response.user_response),
        transcript=response.transcript,
        ai_score=float(response.ai_score) if response.ai_score is not None else None,
        ai_feedback=response.ai_feedback,
        mentor_score=float(response.mentor_score) if response.mentor_score is not None else None,
        mentor_feedback=response.mentor_feedback,
    )


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


def _serialize_review_assignment(
    assignment: ExamReviewAssignment,
    *,
    student_id: UUID | None,
) -> ExamReviewAssignmentItem:
    return ExamReviewAssignmentItem(
        session_id=str(assignment.session_id),
        student_id=str(student_id) if student_id else "",
        mentor_id=str(assignment.mentor_id) if assignment.mentor_id else None,
        status=assignment.status,
        assigned_at=assignment.assigned_at,
        completed_at=assignment.completed_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


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
        phone=mentor.phone,
        current_role=mentor.current_role,
        expertise_areas=mentor.expertise_areas or [],
        experience_years=mentor.experience_years,
        motivation=mentor.motivation,
        average_rating=float(mentor.average_rating or 0.0),
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
        phone=mentor.phone,
        current_role=mentor.current_role,
        expertise_areas=mentor.expertise_areas or [],
        experience_years=mentor.experience_years,
        motivation=mentor.motivation,
        average_rating=float(mentor.average_rating or 0.0),
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


@router.get("/exam-reviews", response_model=list[ExamReviewAssignmentItem])
async def list_exam_review_assignments(
    status_filter: str | None = Query(None, alias="status"),
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor_id = UUID(str(current_user["user_id"]))
    query = (
        db.query(ExamReviewAssignment, ExamSession)
        .join(ExamSession, ExamReviewAssignment.session_id == ExamSession.id)
        .filter(ExamReviewAssignment.mentor_id == mentor_id)
    )
    if status_filter:
        query = query.filter(ExamReviewAssignment.status == status_filter)

    assignments = query.order_by(ExamReviewAssignment.created_at.desc()).all()
    items: list[ExamReviewAssignmentItem] = []
    for assignment, session in assignments:
        items.append(_serialize_review_assignment(assignment, student_id=session.student_id))
    return items


@router.get("/exam-reviews/{session_id}", response_model=ExamReviewAssignmentDetail)
async def get_exam_review_detail(
    session_id: str,
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    mentor_id = UUID(str(current_user["user_id"]))
    assignment = (
        db.query(ExamReviewAssignment)
        .filter(
            ExamReviewAssignment.session_id == session_uuid,
            ExamReviewAssignment.mentor_id == mentor_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Review assignment not found")

    session = db.query(ExamSession).filter(ExamSession.id == session_uuid).first()
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")

    student = db.query(Student).filter(Student.id == session.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    responses = (
        db.query(ExamResponse)
        .filter(ExamResponse.session_id == session.id)
        .all()
    )
    response_map = {item.section_type: item for item in responses}
    response_a = response_map.get("A_INTRO")
    response_d = response_map.get("D_DEBUG")
    if not response_a or not response_d:
        raise HTTPException(status_code=404, detail="Missing Section A or D responses")

    student_payload = ExamReviewStudentPayload(
        student_id=str(student.id),
        name=student.name,
        technical_skills=student.technical_skills,
        resume_url=student.resume_url,
    )

    return ExamReviewAssignmentDetail(
        session_id=str(session.id),
        current_step=session.current_step,
        exam_level=session.exam_level,
        student=student_payload,
        section_a=_build_response_payload(response_a),
        section_d=_build_response_payload(response_d),
    )


@router.post("/exam-reviews/{session_id}/score")
async def submit_exam_review_score(
    session_id: str,
    payload: MentorExamReviewScore,
    current_user: dict = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    mentor_id = UUID(str(current_user["user_id"]))
    assignment = (
        db.query(ExamReviewAssignment)
        .filter(
            ExamReviewAssignment.session_id == session_uuid,
            ExamReviewAssignment.mentor_id == mentor_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Review assignment not found")

    responses = (
        db.query(ExamResponse)
        .filter(ExamResponse.session_id == session_uuid)
        .all()
    )
    response_map = {item.section_type: item for item in responses}
    response_a = response_map.get("A_INTRO")
    response_d = response_map.get("D_DEBUG")
    if not response_a or not response_d:
        raise HTTPException(status_code=404, detail="Missing Section A or D responses")

    feedback_a = payload.section_a.feedback.model_dump()
    feedback_d = payload.section_d.feedback.model_dump()
    if payload.section_d.topic_scores:
        feedback_d["topic_scores"] = payload.section_d.topic_scores

    response_a.mentor_score = payload.section_a.score
    response_a.mentor_feedback = feedback_a
    response_d.mentor_score = payload.section_d.score
    response_d.mentor_feedback = feedback_d

    assignment.status = "completed"
    assignment.completed_at = datetime.now(timezone.utc)

    db.add_all([response_a, response_d, assignment])
    db.commit()

    return {"message": "Mentor review submitted"}

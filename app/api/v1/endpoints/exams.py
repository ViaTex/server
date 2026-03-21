from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.evaluators.exam_question_service import generate_section_b_questions, generate_section_question
from app.ai.evaluators.exam_scoring_service import score_long_response, score_text_response
from app.ai.evaluators.section_a_intro_service import process_section_a_intro_ai
from app.ai.evaluators.section_d_debug_service import process_section_d_debug_ai
from app.ai.evaluator import generate_chat_completion
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import get_current_student
from app.models.exam_response import ExamResponse
from app.models.exam_session import ExamSession
from app.models.user import Student
from app.services.cloudinary_service import CloudinaryService
from app.services.exam_response_service import create_exam_response, update_response_answer
from datetime import datetime, timezone

from app.services.exam_session_service import (
    create_exam_session,
    get_exam_session,
    mark_abandoned,
    set_current_step,
)

router = APIRouter()

SECTION_A_PROMPT = (
    "Please record a 5-10 minute self-introduction covering your background, "
    "core technical skills, recent projects, and career goals."
)


def _is_supported_media(upload: UploadFile) -> bool:
    content_type = (upload.content_type or "").lower()
    if content_type.startswith("video/") or content_type.startswith("audio/"):
        return True

    filename = (upload.filename or "").lower()
    allowed_ext = (
        ".mp4",
        ".mov",
        ".avi",
        ".webm",
        ".mkv",
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".ogg",
    )
    return filename.endswith(allowed_ext)


def _ensure_step(session: ExamSession, step: str) -> None:
    if session.current_step != step:
        raise HTTPException(status_code=409, detail=f"Current step is {session.current_step}")


def _load_student(db: Session, student_id: UUID) -> Student:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/sessions/{session_id}")
async def get_exam_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    return {
        "session_id": str(session.id),
        "current_step": session.current_step,
        "attempt_number": session.attempt_number,
        "exam_level": session.exam_level,
        "is_passed": session.is_passed,
    }


@router.post("/section-a", status_code=status.HTTP_201_CREATED)
async def submit_section_a(
    background_tasks: BackgroundTasks,
    student_id: str = Form(...),
    media_file: UploadFile = File(...),
    exam_level: str = Form("smart_talent"),
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    if not _is_supported_media(media_file):
        raise HTTPException(status_code=400, detail="Only video/audio files are supported")

    try:
        student_uuid = UUID(student_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid student_id") from exc

    if str(student_uuid) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="student_id does not match authenticated student")

    _load_student(db, student_uuid)

    active_session = (
        db.query(ExamSession)
        .filter(
            ExamSession.student_id == student_uuid,
            ExamSession.exam_level == exam_level,
            ExamSession.current_step.in_(["SECTION_A", "SECTION_B", "SECTION_C", "SECTION_D"]),
        )
        .first()
    )
    if active_session:
        mark_abandoned(db, session=active_session)

    file_bytes = await media_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        video_url = CloudinaryService.upload_media_bytes(
            file_bytes,
            folder="exam_sessions/section_a_intro",
            filename=media_file.filename,
            resource_type="auto",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload media: {exc}") from exc

    try:
        session = create_exam_session(db, student_id=student_uuid, exam_level=exam_level)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    response = create_exam_response(
        db,
        session_id=session.id,
        section_type="A_INTRO",
        question_text=SECTION_A_PROMPT,
        user_response=video_url,
    )
    set_current_step(db, session=session, next_step="SECTION_B")

    background_tasks.add_task(process_section_a_intro_ai, str(response.id), video_url)

    return {
        "message": "Section A submitted",
        "session_id": str(session.id),
        "response_id": str(response.id),
        "current_step": session.current_step,
    }


@router.post("/sessions/{session_id}/section-b/question")
async def generate_section_b_question(
    session_id: str,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    _ensure_step(session, "SECTION_B")

    existing = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "B_FUNDAMENTALS",
        )
        .order_by(ExamResponse.id.desc())
        .first()
    )
    if existing:
        question_payload = None
        try:
            question_payload = json.loads(existing.question_text)
        except json.JSONDecodeError:
            question_payload = {
                "mcqs": [],
                "long_questions": [{"id": "l1", "question": existing.question_text}],
            }

        return {
            "response_id": str(existing.id),
            "question_payload": question_payload,
            "section_type": existing.section_type,
        }

    student = _load_student(db, session.student_id)
    try:
        question_payload, answer_key = generate_section_b_questions(student=student)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response = create_exam_response(
        db,
        session_id=session.id,
        section_type="B_FUNDAMENTALS",
        question_text=json.dumps(question_payload),
        user_response="",
        transcript=json.dumps(answer_key),
    )

    return {
        "response_id": str(response.id),
        "question_payload": question_payload,
        "section_type": response.section_type,
    }


@router.post("/sessions/{session_id}/section-b/response")
async def submit_section_b_response(
    session_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    response_id = payload.get("response_id")
    mcq_answers = payload.get("mcq_answers")
    long_answers = payload.get("long_answers")
    if not response_id or mcq_answers is None or long_answers is None:
        raise HTTPException(status_code=400, detail="response_id, mcq_answers, and long_answers are required")
    if not isinstance(mcq_answers, list) or not isinstance(long_answers, list):
        raise HTTPException(status_code=400, detail="mcq_answers and long_answers must be arrays")

    try:
        session_uuid = UUID(session_id)
        response_uuid = UUID(str(response_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id or response_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    _ensure_step(session, "SECTION_B")

    response = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.id == response_uuid,
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "B_FUNDAMENTALS",
        )
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Exam response not found")

    try:
        question_payload = json.loads(response.question_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Stored Section B questions are invalid") from exc

    answer_key = {}
    if response.transcript:
        try:
            answer_key = json.loads(response.transcript)
        except json.JSONDecodeError:
            answer_key = {}

    mcq_answer_map = {item.get("id"): item.get("selected_option") for item in mcq_answers if isinstance(item, dict)}
    long_answer_map = {item.get("id"): item.get("answer") for item in long_answers if isinstance(item, dict)}

    expected_mcq = answer_key.get("mcq_answers") if isinstance(answer_key.get("mcq_answers"), dict) else {}
    expected_long = question_payload.get("long_questions") if isinstance(question_payload.get("long_questions"), list) else []

    if len(expected_mcq) != 15 or len(expected_long) != 5:
        raise HTTPException(status_code=500, detail="Section B question set is incomplete")

    missing_mcq = [qid for qid in expected_mcq.keys() if not mcq_answer_map.get(qid)]
    missing_long = [item.get("id") for item in expected_long if not long_answer_map.get(item.get("id"))]
    if missing_mcq or missing_long:
        raise HTTPException(status_code=400, detail="All Section B answers must be provided")

    correct_count = sum(1 for qid, correct in expected_mcq.items() if mcq_answer_map.get(qid) == correct)
    mcq_score = (correct_count / len(expected_mcq)) * 10 if expected_mcq else 1.0

    long_scores = []
    for item in expected_long:
        long_id = item.get("id")
        question_text = item.get("question")
        answer_text = long_answer_map.get(long_id, "")
        if not question_text:
            continue
        long_scores.append(score_long_response(question_text=question_text, user_response=answer_text))

    long_avg = sum(long_scores) / len(long_scores) if long_scores else 1.0
    final_score = round((mcq_score + long_avg) / 2, 2)
    final_score = max(1.0, min(10.0, final_score))

    payload_to_store = {
        "mcq_answers": mcq_answers,
        "long_answers": long_answers,
    }
    update_response_answer(db, response=response, user_response=json.dumps(payload_to_store))
    response.ai_score = final_score
    if response.hints_used:
        response.ai_score = max(float(response.ai_score or 0.0) - (0.5 * response.hints_used), 0.0)
    db.add(response)
    db.commit()
    db.refresh(response)

    set_current_step(db, session=session, next_step="SECTION_C")

    return {"message": "Section B submitted", "current_step": session.current_step}


@router.post("/sessions/{session_id}/section-c/question")
async def generate_section_c_question(
    session_id: str,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    _ensure_step(session, "SECTION_C")

    existing = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "C_LOGIC",
        )
        .order_by(ExamResponse.id.desc())
        .first()
    )
    if existing:
        return {
            "response_id": str(existing.id),
            "question_text": existing.question_text,
            "section_type": existing.section_type,
        }

    student = _load_student(db, session.student_id)
    question = generate_section_question(section_type="C_LOGIC", student=student)
    response = create_exam_response(
        db,
        session_id=session.id,
        section_type="C_LOGIC",
        question_text=question,
        user_response="",
    )

    return {
        "response_id": str(response.id),
        "question_text": question,
        "section_type": response.section_type,
    }


@router.post("/sessions/{session_id}/section-c/response")
async def submit_section_c_response(
    session_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    response_id = payload.get("response_id")
    user_response = payload.get("user_response")
    if not response_id or user_response is None:
        raise HTTPException(status_code=400, detail="response_id and user_response are required")

    try:
        session_uuid = UUID(session_id)
        response_uuid = UUID(str(response_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id or response_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    _ensure_step(session, "SECTION_C")

    response = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.id == response_uuid,
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "C_LOGIC",
        )
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Exam response not found")

    update_response_answer(db, response=response, user_response=str(user_response))
    analysis = score_text_response(
        section_type="C_LOGIC",
        question_text=response.question_text,
        user_response=str(user_response),
    )
    response.ai_score = analysis.get("score")
    if response.hints_used:
        response.ai_score = max(float(response.ai_score or 0.0) - (0.5 * response.hints_used), 0.0)
    db.add(response)
    db.commit()
    db.refresh(response)

    set_current_step(db, session=session, next_step="SECTION_D")

    return {"message": "Section C submitted", "current_step": session.current_step}


@router.post("/sessions/{session_id}/section-d/question")
async def generate_section_d_question(
    session_id: str,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    _ensure_step(session, "SECTION_D")

    existing = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "D_DEBUG",
        )
        .order_by(ExamResponse.id.desc())
        .first()
    )
    if existing:
        return {
            "response_id": str(existing.id),
            "question_text": existing.question_text,
            "section_type": existing.section_type,
        }

    student = _load_student(db, session.student_id)
    last_logic = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "C_LOGIC",
        )
        .order_by(ExamResponse.id.desc())
        .first()
    )
    prior_context = last_logic.user_response if last_logic else None
    question = generate_section_question(
        section_type="D_DEBUG",
        student=student,
        prior_context=prior_context,
    )

    response = create_exam_response(
        db,
        session_id=session.id,
        section_type="D_DEBUG",
        question_text=question,
        user_response="",
    )

    return {
        "response_id": str(response.id),
        "question_text": question,
        "section_type": response.section_type,
    }


@router.post("/sessions/{session_id}/section-d/response")
async def submit_section_d_response(
    background_tasks: BackgroundTasks,
    session_id: str,
    response_id: str = Form(...),
    media_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    if not _is_supported_media(media_file):
        raise HTTPException(status_code=400, detail="Only video/audio files are supported")

    try:
        session_uuid = UUID(session_id)
        response_uuid = UUID(response_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id or response_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    _ensure_step(session, "SECTION_D")

    response = (
        db.query(ExamResponse)
        .filter(
            ExamResponse.id == response_uuid,
            ExamResponse.session_id == session.id,
            ExamResponse.section_type == "D_DEBUG",
        )
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Exam response not found")

    file_bytes = await media_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        video_url = CloudinaryService.upload_media_bytes(
            file_bytes,
            folder="exam_sessions/section_d_debug",
            filename=media_file.filename,
            resource_type="auto",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload media: {exc}") from exc

    update_response_answer(db, response=response, user_response=video_url)
    session.current_step = "COMPLETED"
    session.completed_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)

    background_tasks.add_task(process_section_d_debug_ai, str(response.id), video_url)

    return {"message": "Section D submitted", "current_step": session.current_step}


@router.post("/sessions/{session_id}/abandon")
async def abandon_exam(
    session_id: str,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    mark_abandoned(db, session=session)
    return {"message": "Exam abandoned", "current_step": session.current_step}


@router.post("/sessions/{session_id}/responses/{response_id}/hint")
async def request_hint(
    session_id: str,
    response_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    try:
        session_uuid = UUID(session_id)
        response_uuid = UUID(response_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id or response_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    response = (
        db.query(ExamResponse)
        .filter(ExamResponse.id == response_uuid, ExamResponse.session_id == session.id)
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Exam response not found")

    if int(response.hints_used or 0) >= 1:
        raise HTTPException(status_code=400, detail="Maximum hints reached for this question")

    question_text = payload.get("question_text") or response.question_text
    student_current_answer = payload.get("student_current_answer") or response.user_response

    redis_client = get_redis_client()
    key = f"exam_hints:{session_id}:{response_id}"
    cached = redis_client.get(key)
    previous_hints = []
    if cached:
        try:
            previous_hints = json.loads(cached)
        except json.JSONDecodeError:
            previous_hints = []

    system_prompt = (
        "You are an exam assistant. Provide a short, helpful conceptual nudge. "
        "DO NOT give the exact answer. You have already provided the following hints: "
        f"{previous_hints}. You must provide a NEW hint that is progressively more specific than the previous ones."
    )
    user_prompt = (
        f"Question: {question_text}\n"
        f"Student response so far: {student_current_answer}"
    )
    hint_text = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.4,
        max_tokens=120,
    )

    if not hint_text:
        raise HTTPException(status_code=500, detail="Failed to generate hint")

    previous_hints.append(hint_text)
    redis_client.setex(key, 14400, json.dumps(previous_hints))

    response.hints_used = int(response.hints_used or 0) + 1
    if response.ai_score is not None:
        response.ai_score = max(float(response.ai_score) - 0.5, 0.0)
    db.add(response)
    db.commit()
    db.refresh(response)

    return {"hint": hint_text}


@router.post("/{session_id}/responses/{response_id}/chat")
async def exam_response_chat(
    session_id: str,
    response_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    user_message = payload.get("user_message")
    current_user_code_or_text = payload.get("current_user_code_or_text") or ""
    if not user_message or not isinstance(user_message, str):
        raise HTTPException(status_code=400, detail="user_message is required")

    try:
        session_uuid = UUID(session_id)
        response_uuid = UUID(response_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session_id or response_id") from exc

    session = get_exam_session(db, session_id=session_uuid, student_id=UUID(current_user["user_id"]))
    response = (
        db.query(ExamResponse)
        .filter(ExamResponse.id == response_uuid, ExamResponse.session_id == session.id)
        .first()
    )
    if not response:
        raise HTTPException(status_code=404, detail="Exam response not found")

    redis_client = get_redis_client()
    history_key = f"exam_chat_history:{session_id}:{response_id}"
    cached = redis_client.get(history_key)
    history = []
    if cached:
        try:
            history = json.loads(cached)
        except json.JSONDecodeError:
            history = []

    first_message = len(history) == 0

    history.append({"role": "user", "content": user_message})

    question_text = response.question_text or ""
    if question_text and user_message.strip() == question_text.strip():
        assistant_reply = (
            "I see you are looking at the main prompt. What part of this problem is confusing you, "
            "or how would you break this down into smaller steps?"
        )
    else:
        system_prompt = (
            "You are a strict but helpful exam proctor and Socratic tutor. "
            f"The user is currently trying to answer this exam question: {question_text}. "
            "CRITICAL RULE: Under NO circumstances are you allowed to give the direct answer, "
            "write the exact code needed, or solve the problem for the user. "
            "If the user copy-pastes the exam question directly into the chat, DO NOT answer it. "
            "Instead, ask them: 'I see you are looking at the main prompt. What part of this problem is confusing you, "
            "or how would you break this down into smaller steps?' "
            "Provide short, guiding nudges. Point out syntax errors in their current code if they ask, "
            "but make them write the fix."
        )

        history_text = "\n".join(
            f"{item.get('role')}: {item.get('content')}" for item in history if isinstance(item, dict)
        )
        user_prompt = (
            f"Question: {question_text}\n"
            f"Current user work: {current_user_code_or_text}\n"
            f"Chat history:\n{history_text}\n"
            f"User message: {user_message}"
        )

        assistant_reply = generate_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=220,
        )

    if not assistant_reply:
        assistant_reply = "I cannot respond right now. Try asking about a specific part you are stuck on."

    history.append({"role": "assistant", "content": assistant_reply})
    redis_client.setex(history_key, 14400, json.dumps(history))

    if first_message:
        response.hints_used = int(response.hints_used or 0) + 1
        if response.ai_score is not None:
            response.ai_score = max(float(response.ai_score) - 0.5, 0.0)
        db.add(response)
        db.commit()
        db.refresh(response)

    return {"reply": assistant_reply}

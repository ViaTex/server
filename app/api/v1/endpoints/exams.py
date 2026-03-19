from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_student
from app.models.user import Student
from app.services.cloudinary_service import CloudinaryService
from app.services.exam_session_service import create_intro_exam_session
from app.ai.evaluators.section_a_intro_service import process_section_a_intro_ai

router = APIRouter()


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


@router.post("/section-intro", status_code=status.HTTP_201_CREATED)
async def create_section_intro_session(
    background_tasks: BackgroundTasks,
    student_id: str = Form(...),
    media_file: UploadFile = File(...),
    exam_level: str = Form("section_1"),
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

    student = db.query(Student).filter(Student.id == student_uuid).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

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

    exam_session = create_intro_exam_session(
        db,
        student_id=student_uuid,
        exam_level=exam_level,
        video_url=video_url,
    )

    background_tasks.add_task(
        process_section_a_intro_ai,
        str(exam_session.id),
        video_url,
    )

    return {
        "message": "Section 1 introduction session created successfully",
        "status": "success",
        "exam_session_id": str(exam_session.id),
    }

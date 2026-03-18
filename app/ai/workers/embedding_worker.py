from fastapi import BackgroundTasks

from app.ai.services.student_ai_service import process_student_embedding
from app.core.database import SessionLocal


def _run_embedding_job(student_id: str) -> None:
    db = SessionLocal()
    try:
        process_student_embedding(student_id, db)
    finally:
        db.close()


def enqueue_student_embedding(background_tasks: BackgroundTasks, student_id: str) -> None:
    background_tasks.add_task(_run_embedding_job, student_id)

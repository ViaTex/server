from fastapi import BackgroundTasks

from app.ai.services.profile_history_service import process_student_profile_history
from app.core.database import SessionLocal


def _run_profile_history_job(student_id: str, change_type: str | None = None) -> None:
    db = SessionLocal()
    try:
        process_student_profile_history(student_id, db, change_type=change_type)
    finally:
        db.close()


def enqueue_student_profile_history_update(
    background_tasks: BackgroundTasks,
    student_id: str,
    *,
    change_type: str | None = None,
) -> None:
    background_tasks.add_task(_run_profile_history_job, student_id, change_type)

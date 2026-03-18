from fastapi import BackgroundTasks

from app.ai.services.student_skill_profile_service import process_student_skill_profile
from app.core.database import SessionLocal


def _run_skill_profile_job(student_id: str) -> None:
    db = SessionLocal()
    try:
        process_student_skill_profile(student_id, db)
    finally:
        db.close()


def enqueue_student_skill_profile_update(
    background_tasks: BackgroundTasks,
    student_id: str,
) -> None:
    background_tasks.add_task(_run_skill_profile_job, student_id)

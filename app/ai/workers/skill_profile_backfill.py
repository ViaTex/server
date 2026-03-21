from app.ai.repositories.student_skill_profile_repo import list_students_for_backfill
from app.ai.evaluators.student_skill_profile_service import process_student_skill_profile
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal


def backfill_skill_profiles(batch_size: int = 100) -> dict:
    db = SessionLocal()
    processed = 0
    failed = 0
    offset = 0

    try:
        while True:
            students = list_students_for_backfill(db, offset=offset, limit=batch_size)
            if not students:
                break

            for student in students:
                try:
                    success = process_student_skill_profile(str(student.id), db)
                    if success:
                        processed += 1
                    else:
                        failed += 1
                except Exception as exc:
                    failed += 1
                    ai_error(f"Skill profile backfill failed for student_id={student.id}: {exc}")

            offset += batch_size

        ai_log(f"Skill profile backfill completed. processed={processed}, failed={failed}")
        return {"processed": processed, "failed": failed}
    finally:
        db.close()

import uuid

from app.ai.repositories.student_skill_profile_repo import (
    get_student_by_id,
    update_skill_profile,
)
from app.ai.skill_profile.generator import generate_skill_profile
from app.ai.utils.logger import ai_error, ai_log


def process_student_skill_profile(student_id, db):
    try:
        ai_log("Skill profile generation started")

        student_uuid = uuid.UUID(str(student_id))
        student = get_student_by_id(db, student_uuid)
        if not student:
            raise ValueError("Student not found")

        skill_profile = generate_skill_profile(student)
        ai_log("Skill profile generated")

        update_skill_profile(db, student, skill_profile)
        ai_log("Skill profile updated in database")
        return True
    except Exception as exc:
        ai_error(f"Skill profile update failed: {exc}")
        return False

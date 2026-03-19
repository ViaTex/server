from app.ai.services.profile_history_service import process_student_profile_history


def process_student_skill_profile(student_id, db):
    """Backward-compatible wrapper for old worker entrypoint.

    Skill profile and embedding are now captured in user_profile_history snapshots.
    """
    return process_student_profile_history(student_id, db, change_type="legacy_skill_profile_job")

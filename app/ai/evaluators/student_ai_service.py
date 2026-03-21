from app.ai.evaluators.profile_history_service import process_student_profile_history


def process_student_embedding(student_id, db):
    """Backward-compatible wrapper for legacy embedding jobs.

    Embeddings are now persisted in user_profile_history rows.
    """
    return process_student_profile_history(student_id, db, change_type="legacy_embedding_job")

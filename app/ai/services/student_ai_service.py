import uuid

from app.ai.embedding.formatter import format_student_profile_text
from app.ai.embedding.generator import generate_embedding
from app.ai.repositories.student_ai_repo import get_student_by_id, update_profile_vector
from app.ai.utils.logger import ai_error, ai_log


def process_student_embedding(student_id, db):
    try:
        ai_log("Generating embedding...")
        ai_log(f"Generating embedding for student_id={student_id}")

        student_uuid = uuid.UUID(str(student_id))
        student = get_student_by_id(db, student_uuid)
        if not student:
            raise ValueError("Student not found")

        profile_text = format_student_profile_text(student)

        ai_log("Embedding generation in progress...")
        vector = generate_embedding(profile_text)
        update_profile_vector(db, student, vector)

        ai_log("Embedding stored successfully")
    except Exception as exc:
        ai_error(f"Embedding failed: {exc}")

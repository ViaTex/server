import json
import uuid

from app.ai.embeddings.generator import generate_embedding
from app.ai.profile_history.snapshot import build_profile_snapshot, snapshot_to_embedding_text
from app.ai.repositories.user_profile_history_repo import (
    get_latest_profile_history,
    get_student_by_id,
    insert_profile_history_entry,
)
from app.ai.utils.logger import ai_error, ai_log


def _snapshot_changed(previous_snapshot: dict | None, current_snapshot: dict) -> bool:
    if previous_snapshot is None:
        return True
    previous = json.dumps(previous_snapshot, ensure_ascii=True, sort_keys=True)
    current = json.dumps(current_snapshot, ensure_ascii=True, sort_keys=True)
    return previous != current


def process_student_profile_history(
    student_id: str,
    db,
    *,
    change_type: str | None = None,
) -> bool:
    """Generate snapshot+embedding and persist a new history row only when tracked fields changed."""
    try:
        student_uuid = uuid.UUID(str(student_id))
        student = get_student_by_id(db, student_uuid)
        if not student:
            raise ValueError("Student not found")

        snapshot = build_profile_snapshot(student)
        latest = get_latest_profile_history(db, student_uuid)
        previous_snapshot = latest.profile_snapshot if latest else None

        if not _snapshot_changed(previous_snapshot, snapshot):
            ai_log(f"No tracked profile change for student_id={student_id}; skipping history insert")
            return False

        embedding_text = snapshot_to_embedding_text(snapshot)
        embedding = generate_embedding(embedding_text)

        insert_profile_history_entry(
            db,
            student_id=student_uuid,
            profile_snapshot=snapshot,
            embedding=embedding,
            change_type=change_type,
        )
        ai_log(f"Profile history inserted for student_id={student_id}")
        return True
    except Exception as exc:
        ai_error(f"Profile history generation failed for student_id={student_id}: {exc}")
        return False

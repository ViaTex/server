from app.ai.profile_history.snapshot import build_profile_snapshot
from app.models.user import Student
from app.models.user_profile_history import UserProfileHistory


def get_student_by_id(db, student_id):
    return db.query(Student).filter(Student.id == student_id).first()


def insert_profile_history_embedding(db, student, embedding: list[float]) -> None:
    """Store a generated embedding as a new user_profile_history row."""
    snapshot = build_profile_snapshot(student)
    entry = UserProfileHistory(
        user_id=student.id,
        profile_snapshot=snapshot,
        embedding=embedding,
        change_type="legacy_embedding_write",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)


def get_latest_profile_history(db, student_id):
    return (
        db.query(UserProfileHistory)
        .filter(UserProfileHistory.user_id == student_id)
        .order_by(UserProfileHistory.created_at.desc())
        .first()
    )

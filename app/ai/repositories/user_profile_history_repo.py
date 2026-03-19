from app.models.user import Student
from app.models.user_profile_history import UserProfileHistory


def get_student_by_id(db, student_id):
    return db.query(Student).filter(Student.id == student_id).first()


def get_latest_profile_history(db, student_id):
    return (
        db.query(UserProfileHistory)
        .filter(UserProfileHistory.user_id == student_id)
        .order_by(UserProfileHistory.created_at.desc())
        .first()
    )


def insert_profile_history_entry(
    db,
    *,
    student_id,
    profile_snapshot: dict,
    embedding: list[float],
    change_type: str | None = None,
):
    entry = UserProfileHistory(
        user_id=student_id,
        profile_snapshot=profile_snapshot,
        embedding=embedding,
        change_type=change_type,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

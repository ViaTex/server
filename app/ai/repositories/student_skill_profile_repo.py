from app.models.user import Student


def get_student_by_id(db, student_id):
    return db.query(Student).filter(Student.id == student_id).first()


def update_skill_profile(db, student, skill_profile: dict) -> None:
    student.skill_profile = skill_profile
    db.add(student)
    db.commit()
    db.refresh(student)


def list_students_for_backfill(db, offset: int, limit: int):
    return (
        db.query(Student)
        .order_by(Student.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

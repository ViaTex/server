from app.models.user import Student


def get_student_by_id(db, student_id):
    return db.query(Student).filter(Student.id == student_id).first()


def list_students_for_backfill(db, offset: int, limit: int):
    return (
        db.query(Student)
        .order_by(Student.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

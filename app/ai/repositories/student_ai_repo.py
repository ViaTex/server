from app.models.user import Student


def get_student_by_id(db, student_id):
    return db.query(Student).filter(Student.id == student_id).first()


def update_profile_vector(db, student, vector: list[float]) -> None:
    student.profile_vector = vector
    db.add(student)
    db.commit()
    db.refresh(student)

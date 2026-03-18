from app.ai.repositories.student_ai_repo import update_profile_vector


class DummyDB:
    def __init__(self):
        self.committed = False
        self.refreshed = False

    def add(self, _obj):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        self.refreshed = True


class DummyStudent:
    profile_vector = None


def test_vector_is_stored_in_student_record():
    db = DummyDB()
    student = DummyStudent()
    vector = [0.1, 0.2, 0.3]

    update_profile_vector(db, student, vector)

    assert student.profile_vector == vector
    assert db.committed is True
    assert db.refreshed is True

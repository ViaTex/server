from app.ai.repositories.student_ai_repo import insert_profile_history_embedding


class DummyDB:
    def __init__(self):
        self.committed = False
        self.refreshed = False
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        self.refreshed = True


class DummyStudent:
    id = "student-1"
    technical_skills = "Python"
    soft_skills = "Communication"
    certifications = "AWS"
    preferred_industry = "Software"
    job_roles_of_interest = "Backend Developer"
    extracurricular_activities = "Hackathons"
    experience = [{"company_name": "Acme", "role": "Intern"}]
    bio = "Student bio"
    projects = []
    custom_achievements = []
    education = []


def test_embedding_is_stored_in_profile_history_record():
    db = DummyDB()
    student = DummyStudent()
    vector = [0.1, 0.2, 0.3]

    insert_profile_history_embedding(db, student, vector)

    assert len(db.added) == 1
    assert db.added[0].user_id == student.id
    assert db.added[0].embedding == vector
    assert db.committed is True
    assert db.refreshed is True

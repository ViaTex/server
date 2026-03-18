from types import SimpleNamespace

from app.ai.embedding.validator import has_meaningful_change


def test_email_only_update_does_not_trigger_embedding():
    old_student = SimpleNamespace(
        technical_skills="python, sql",
        soft_skills="communication",
        certifications="none",
        preferred_industry="software",
        projects=[{"title": "API"}],
        internship_experience="internship",
        bio="bio",
        extracurricular_activities="sports",
        custom_achievements=[{"title": "winner"}],
        education=[{"institution": "ABC College"}],
    )

    updated_data = {"email": "new@example.com"}

    assert has_meaningful_change(old_student, updated_data) is False


def test_skills_update_triggers_embedding():
    old_student = SimpleNamespace(
        technical_skills="python, sql",
        soft_skills="communication",
        certifications="none",
        preferred_industry="software",
        projects=[{"title": "API"}],
        internship_experience="internship",
        bio="bio",
        extracurricular_activities="sports",
        custom_achievements=[{"title": "winner"}],
        education=[{"institution": "ABC College"}],
    )

    updated_data = {"technical_skills": "python, sql, fastapi"}

    assert has_meaningful_change(old_student, updated_data) is True


def test_same_value_update_does_not_trigger_embedding():
    old_student = SimpleNamespace(
        technical_skills="python, sql",
        soft_skills="communication",
        certifications="none",
        preferred_industry="software",
        projects=[{"title": "API"}],
        internship_experience="internship",
        bio="bio",
        extracurricular_activities="sports",
        custom_achievements=[{"title": "winner"}],
        education=[{"institution": "ABC College"}],
    )

    updated_data = {"technical_skills": "python, sql"}

    assert has_meaningful_change(old_student, updated_data) is False

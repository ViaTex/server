from app.ai.utils.helpers import value_to_text


def format_student_profile_text(student) -> str:
    return (
        "Name: {name} | "
        "Tech Skills: {technical_skills} | "
        "Soft Skills: {soft_skills} | "
        "Certifications: {certifications} | "
        "Industry: {preferred_industry} | "
        "Projects: {projects} | "
        "Internship: {internship_experience} | "
        "Achievements: {custom_achievements} | "
        "Education: {education} | "
        "Activities: {extracurricular_activities} | "
        "Bio: {bio}"
    ).format(
        name=value_to_text(getattr(student, "name", "")),
        technical_skills=value_to_text(getattr(student, "technical_skills", "")),
        soft_skills=value_to_text(getattr(student, "soft_skills", "")),
        certifications=value_to_text(getattr(student, "certifications", "")),
        preferred_industry=value_to_text(getattr(student, "preferred_industry", "")),
        projects=value_to_text(getattr(student, "projects", "")),
        internship_experience=value_to_text(getattr(student, "internship_experience", "")),
        custom_achievements=value_to_text(getattr(student, "custom_achievements", "")),
        education=value_to_text(getattr(student, "education", "")),
        extracurricular_activities=value_to_text(
            getattr(student, "extracurricular_activities", "")
        ),
        bio=value_to_text(getattr(student, "bio", "")),
    )

import json
import re
from typing import Any


# Fields that should trigger a new profile history version when they change.
TRACKED_PROFILE_FIELDS = [
    "technical_skills",
    "soft_skills",
    "certifications",
    "preferred_industry",
    "job_roles_of_interest",
    "extracurricular_activities",
    "experience",
    "bio",
    "projects",
    "custom_achievements",
    "education",
]


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        return [token.strip() for token in re.split(r"[,;\n]+", text) if token.strip()]
    text = str(value).strip()
    return [text] if text else []


def _to_list_of_dicts(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def build_profile_snapshot(student) -> dict:
    """Build normalized JSON snapshot used for versioned profile history rows."""
    return {
        "skills": _to_list(getattr(student, "technical_skills", None)),
        "soft_skills": _to_list(getattr(student, "soft_skills", None)),
        "certifications": _to_list(getattr(student, "certifications", None)),
        "preferred_industry": _to_list(getattr(student, "preferred_industry", None)),
        "job_roles_of_interest": _to_list(getattr(student, "job_roles_of_interest", None)),
        "extracurricular_activity": _to_list(
            getattr(student, "extracurricular_activities", None)
        ),
        "experience": _to_list_of_dicts(getattr(student, "experience", None)),
        "bio": _to_text(getattr(student, "bio", None)),
        "projects": _to_list_of_dicts(getattr(student, "projects", None)),
        "custom_achievement": _to_list_of_dicts(
            getattr(student, "custom_achievements", None)
        ),
        "education": _to_list_of_dicts(getattr(student, "education", None)),
    }


def snapshot_to_embedding_text(snapshot: dict) -> str:
    """Serialize snapshot into stable text for deterministic embedding generation."""
    return json.dumps(snapshot, ensure_ascii=True, sort_keys=True)

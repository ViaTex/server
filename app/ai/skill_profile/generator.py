import re
from typing import Any

from app.ai.utils.helpers import value_to_text


DOMAIN_KEYWORDS = {
    "ai": "AI",
    "machine learning": "ML",
    "ml": "ML",
    "backend": "Backend",
    "api": "Backend",
    "data": "Data Science",
    "data science": "Data Science",
    "analytics": "Data Science",
    "frontend": "Frontend",
    "web": "Web Development",
    "mobile": "Mobile Development",
    "cloud": "Cloud",
    "devops": "DevOps",
    "cyber": "Cybersecurity",
    "security": "Cybersecurity",
}

ADVANCED_TOPIC_KEYWORDS = {
    "transformer": "Transformers",
    "transformers": "Transformers",
    "gnn": "GNN",
    "graph neural": "GNN",
    "llm": "LLM",
    "large language model": "LLM",
    "rag": "RAG",
    "retrieval augmented": "RAG",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
}


def _contains_keyword(source: str, keyword: str) -> bool:
    pattern = rf"\b{re.escape(keyword)}\b"
    return re.search(pattern, source) is not None


def _tokenize_text(value: Any) -> list[str]:
    text = value_to_text(value).lower()
    if not text:
        return []
    tokens = re.split(r"[,;|/\\\n]+", text)
    cleaned = [token.strip() for token in tokens if token and token.strip()]
    return cleaned


def _projects_text(projects: Any) -> str:
    if isinstance(projects, list):
        chunks = []
        for project in projects:
            if isinstance(project, dict):
                chunks.append(value_to_text(project.get("title", "")))
                chunks.append(value_to_text(project.get("description", "")))
                chunks.append(value_to_text(project.get("technologies_used", [])))
        return " ".join(chunks).strip().lower()
    return value_to_text(projects).lower()


def _extract_domains(technical_skills: Any, preferred_industry: Any, projects: Any) -> list[str]:
    source = " ".join(
        [
            value_to_text(technical_skills).lower(),
            value_to_text(preferred_industry).lower(),
            _projects_text(projects),
        ]
    )
    domains: list[str] = []
    for keyword, mapped_domain in DOMAIN_KEYWORDS.items():
        if _contains_keyword(source, keyword) and mapped_domain not in domains:
            domains.append(mapped_domain)
    return domains


def _extract_core_skills(technical_skills: Any, soft_skills: Any) -> list[str]:
    core_skills: list[str] = []
    for value in [technical_skills, soft_skills]:
        for token in _tokenize_text(value):
            normalized = re.sub(r"\s+", " ", token).strip().lower()
            if normalized and normalized not in core_skills:
                core_skills.append(normalized)
    return core_skills


def _extract_advanced_topics(technical_skills: Any, projects: Any) -> list[str]:
    source = " ".join(
        [
            value_to_text(technical_skills).lower(),
            _projects_text(projects),
        ]
    )
    advanced_topics: list[str] = []
    for keyword, topic in ADVANCED_TOPIC_KEYWORDS.items():
        if _contains_keyword(source, keyword) and topic not in advanced_topics:
            advanced_topics.append(topic)
    return advanced_topics


def _compute_experience_level(internship_experience: Any, projects: Any, advanced_topics: list[str]) -> str:
    has_internship = bool(value_to_text(internship_experience).strip())
    has_projects = False
    if isinstance(projects, list):
        has_projects = len(projects) > 0
    else:
        has_projects = bool(value_to_text(projects).strip())

    if has_internship and advanced_topics:
        return "advanced"
    if has_projects:
        return "intermediate"
    return "beginner"


def generate_skill_profile(student) -> dict:
    advanced_topics = _extract_advanced_topics(
        getattr(student, "technical_skills", ""),
        getattr(student, "projects", []),
    )

    return {
        "domains": _extract_domains(
            getattr(student, "technical_skills", ""),
            getattr(student, "preferred_industry", ""),
            getattr(student, "projects", []),
        ),
        "core_skills": _extract_core_skills(
            getattr(student, "technical_skills", ""),
            getattr(student, "soft_skills", ""),
        ),
        "advanced_topics": advanced_topics,
        "experience_level": _compute_experience_level(
            getattr(student, "internship_experience", ""),
            getattr(student, "projects", []),
            advanced_topics,
        ),
    }

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import date
from typing import Any, Dict, Optional

import httpx
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import Gender, Student
from app.models.resume_embedding import ResumeEmbedding
from ai.embedding_generator import EmbeddingGenerator, EmbeddingInput
from ai.resume_parser import parse_resume_pdf_bytes


logger = logging.getLogger(__name__)

RESUME_QUEUE_KEY = "resume_parse_queue"
JOB_STATUS_KEY_PREFIX = "resume_job:"


def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _set_job_status(job_id: str, status: str, *, error: str = "") -> None:
    r = _redis()
    mapping: Dict[str, str] = {"status": status}
    if error:
        mapping["error"] = error
    r.hset(f"{JOB_STATUS_KEY_PREFIX}{job_id}", mapping=mapping)
    r.expire(f"{JOB_STATUS_KEY_PREFIX}{job_id}", 60 * 60)


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except Exception:
            return None
    return None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "")
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return date.fromisoformat(s)
        except Exception:
            return None
    return None


def _parse_gender(value: Any) -> Optional[Gender]:
    if not value or not isinstance(value, str):
        return None
    s = value.strip().lower()
    if s in ("male", "m"):
        return Gender.MALE
    if s in ("female", "f"):
        return Gender.FEMALE
    if s in ("other", "non-binary", "nonbinary"):
        return Gender.OTHER
    return None


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _set_if_blank(obj: Any, attr: str, value: Any) -> None:
    if value is None:
        return
    current = getattr(obj, attr)
    if _is_blank(current):
        setattr(obj, attr, value)


def _join_list(items: Any) -> str:
    if not items:
        return ""
    if isinstance(items, str):
        return items
    if isinstance(items, list):
        cleaned = []
        for i in items:
            if isinstance(i, str):
                s = i.strip()
                if s:
                    cleaned.append(s)
        return ", ".join(cleaned)
    return ""


def _projects_to_student_json(parsed_projects: Any) -> list[dict]:
    out: list[dict] = []
    if not parsed_projects:
        return out

    for p in parsed_projects:
        technologies = getattr(p, "technologies_used", None)
        out.append(
            {
                "id": str(uuid.uuid4()),
                "title": getattr(p, "title", "") or "",
                "description": getattr(p, "description", "") or "",
                "skills_used": [],
                "technologies_used": technologies if isinstance(technologies, list) else [],
                "start_date": getattr(p, "start_date", "") or "",
                "end_date": getattr(p, "end_date", "") or "",
                "project_url": "",
                "github_url": getattr(p, "github_url", "") or "",
                "demo_url": getattr(p, "demo_url", "") or "",
                "images": [],
                "status": "completed",
            }
        )
    return out


def _achievements_to_student_json(custom_achievements: Any) -> list[dict]:
    out: list[dict] = []
    if not custom_achievements:
        return out

    if isinstance(custom_achievements, list):
        for item in custom_achievements:
            if isinstance(item, str) and item.strip():
                out.append(
                    {
                        "id": str(uuid.uuid4()),
                        "title": item.strip(),
                        "category": "Other",
                        "description": "",
                        "tags": [],
                        "url": "",
                        "date": "",
                    }
                )
    return out


def _build_embedding_inputs(student: Student) -> list[EmbeddingInput]:
    skills_text = "\n".join(
        [
            f"Technical Skills: {student.technical_skills or ''}",
            f"Soft Skills: {student.soft_skills or ''}",
        ]
    ).strip()

    projects_text = ""
    if isinstance(student.projects, list) and student.projects:
        parts: list[str] = []
        for p in student.projects:
            if not isinstance(p, dict):
                continue
            title = (p.get("title") or "").strip()
            desc = (p.get("description") or "").strip()
            tech = p.get("technologies_used")
            tech_str = ", ".join([t.strip() for t in tech if isinstance(t, str) and t.strip()]) if isinstance(tech, list) else ""
            block = "\n".join([
                f"Project: {title}" if title else "Project",
                f"Description: {desc}" if desc else "",
                f"Technologies: {tech_str}" if tech_str else "",
            ]).strip()
            if block:
                parts.append(block)
        projects_text = "\n\n".join(parts).strip()

    experience_text = "\n".join(
        [
            f"Internship Experience: {student.internship_experience or ''}",
            f"Extracurricular Activities: {student.extracurricular_activities or ''}",
        ]
    ).strip()

    bio_text = (student.bio or "").strip()

    return [
        EmbeddingInput(section="skills", content=skills_text),
        EmbeddingInput(section="projects", content=projects_text),
        EmbeddingInput(section="experience", content=experience_text),
        EmbeddingInput(section="bio", content=bio_text),
    ]


async def _process_job(db: Session, payload: dict) -> None:
    job_id = payload.get("job_id")
    student_id = payload.get("student_id")
    resume_url = payload.get("resume_url")

    if not job_id or not student_id or not resume_url:
        raise ValueError("Invalid job payload")

    try:
        student_uuid = uuid.UUID(str(student_id))
    except Exception as e:
        raise ValueError("Invalid student_id") from e

    student = db.query(Student).filter(Student.id == student_uuid).first()
    if not student:
        raise ValueError("Student not found")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(resume_url)
        resp.raise_for_status()
        pdf_bytes = resp.content

    parsed = await parse_resume_pdf_bytes(pdf_bytes)

    # Map parsed fields to existing Student columns (fill blanks, don't overwrite user edits).
    _set_if_blank(student, "name", parsed.name or None)
    _set_if_blank(student, "phone", parsed.phone or None)

    _set_if_blank(student, "dob", _parse_date(parsed.dob))
    _set_if_blank(student, "gender", _parse_gender(parsed.gender))

    _set_if_blank(student, "city", parsed.city or None)
    _set_if_blank(student, "state", parsed.state or None)
    _set_if_blank(student, "country", parsed.country or None)

    _set_if_blank(student, "institution", parsed.institution or None)
    _set_if_blank(student, "degree", parsed.degree or None)
    _set_if_blank(student, "branch", parsed.branch or None)
    _set_if_blank(student, "major", parsed.major or None)
    _set_if_blank(student, "graduation_year", _parse_int(parsed.graduation_year))

    _set_if_blank(student, "tenth_grade_percentage", _parse_float(parsed.tenth_grade_percentage))
    _set_if_blank(student, "twelfth_grade_percentage", _parse_float(parsed.twelfth_grade_percentage))
    _set_if_blank(student, "btech_cgpa", _parse_float(parsed.btech_cgpa))

    _set_if_blank(student, "technical_skills", _join_list(parsed.technical_skills) or None)
    _set_if_blank(student, "soft_skills", _join_list(parsed.soft_skills) or None)
    _set_if_blank(student, "certifications", _join_list(parsed.certifications) or None)

    _set_if_blank(student, "preferred_industry", parsed.preferred_industry or None)
    _set_if_blank(student, "job_roles_of_interest", _join_list(parsed.job_roles_of_interest) or None)
    _set_if_blank(student, "location_preferences", _join_list(parsed.location_preferences) or None)
    _set_if_blank(student, "language_proficiency", _join_list(parsed.language_proficiency) or None)

    _set_if_blank(student, "extracurricular_activities", _join_list(parsed.extracurricular_activities) or None)
    _set_if_blank(student, "internship_experience", _join_list(parsed.internship_experience) or None)

    _set_if_blank(student, "linkedin_profile", parsed.linkedin_profile or None)
    _set_if_blank(student, "github_profile", parsed.github_profile or None)
    _set_if_blank(student, "personal_website", parsed.personal_website or None)

    _set_if_blank(student, "bio", parsed.bio or None)

    if _is_blank(student.projects):
        student.projects = _projects_to_student_json(parsed.projects)

    if _is_blank(student.custom_achievements):
        student.custom_achievements = _achievements_to_student_json(parsed.custom_achievements)

    db.add(student)
    db.commit()
    db.refresh(student)

    # Embeddings: replace existing sections for this student.
    embedding_inputs = _build_embedding_inputs(student)
    generator = EmbeddingGenerator()
    rows = generator.generate(embedding_inputs)

    if rows:
        sections = [r["section"] for r in rows]
        db.query(ResumeEmbedding).filter(
            ResumeEmbedding.student_id == student.id,
            ResumeEmbedding.section.in_(sections),
        ).delete(synchronize_session=False)

        for r in rows:
            db.add(
                ResumeEmbedding(
                    student_id=student.id,
                    section=r["section"],
                    content=r["content"],
                    embedding=r["embedding"],
                )
            )
        db.commit()


async def worker_loop() -> None:
    logger.info("Resume worker started")
    r = _redis()

    while True:
        try:
            item = r.blpop(RESUME_QUEUE_KEY, timeout=5)
            if not item:
                continue

            _queue, raw = item
            payload = json.loads(raw)
            job_id = payload.get("job_id", "")

            if job_id:
                _set_job_status(job_id, "running")

            db = SessionLocal()
            try:
                await _process_job(db, payload)
                if job_id:
                    _set_job_status(job_id, "succeeded")
            except Exception as e:
                logger.exception("Resume job failed")
                if job_id:
                    _set_job_status(job_id, "failed", error=str(e))
            finally:
                db.close()

        except Exception:
            logger.exception("Worker loop error")
            time.sleep(1)


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())

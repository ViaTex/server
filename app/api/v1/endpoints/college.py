from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_college
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.job import Job
from app.models.user import College, SkillEvaluation, SkillEvaluationStatus, Student

router = APIRouter()


def _college_student_ids(db: Session, college_id: str) -> list[UUID]:
    """Return all student UUIDs linked to this college."""
    students = db.query(Student).filter(Student.college_id == str(college_id)).all()
    return [s.id for s in students]


# ── Placements feed ──────────────────────────────────────────────────────────

@router.get("/placements")
async def college_placements(
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    """Real-time feed of all placed students from this college."""
    college_id = str(current_user["user_id"])
    student_ids = _college_student_ids(db, college_id)
    if not student_ids:
        return []

    rows = (
        db.query(JobApplication, Student, Job)
        .join(Student, Student.id == JobApplication.student_id)
        .join(Job, Job.id == JobApplication.job_id)
        .filter(
            JobApplication.student_id.in_(student_ids),
            JobApplication.status == ApplicationStatus.SELECTED,
        )
        .order_by(JobApplication.placed_at.desc())
        .all()
    )

    result = []
    for app, student, job in rows:
        result.append({
            "student_id": str(student.id),
            "student_name": student.name,
            "student_email": student.email,
            "des_score": float(student.current_des_score or 0),
            "badge": student.badge,
            "job_title": app.placed_job_title or job.title,
            "company_name": app.placed_by_corporate_name or job.company_name,
            "placed_at": app.placed_at,
            "application_id": str(app.id),
        })
    return result


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def college_analytics(
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    """Aggregate analytics: placement rate, avg DES, verification stats, top companies."""
    college_id = str(current_user["user_id"])
    students = db.query(Student).filter(Student.college_id == college_id).all()
    student_ids = [s.id for s in students]
    total_students = len(students)

    if total_students == 0:
        return {
            "total_students": 0,
            "placed_count": 0,
            "placement_rate_pct": 0,
            "avg_des_score": 0,
            "verified_count": 0,
            "viva_scheduled_count": 0,
            "no_viva_count": 0,
            "des_distribution": [],
            "top_companies": [],
        }

    # Placed count
    placed_count = (
        db.query(JobApplication)
        .filter(
            JobApplication.student_id.in_(student_ids),
            JobApplication.status == ApplicationStatus.SELECTED,
        )
        .count()
    )

    # Average DES
    avg_des_raw = db.query(func.avg(Student.current_des_score)).filter(
        Student.id.in_(student_ids)
    ).scalar()
    avg_des = round(float(avg_des_raw or 0), 2)

    # Verification breakdown
    verified_ids = set(
        row[0]
        for row in db.query(SkillEvaluation.student_id)
        .filter(
            SkillEvaluation.student_id.in_(student_ids),
            SkillEvaluation.status == SkillEvaluationStatus.EVALUATED,
        )
        .distinct()
        .all()
    )
    viva_scheduled_ids = set(
        row[0]
        for row in db.query(SkillEvaluation.student_id)
        .filter(
            SkillEvaluation.student_id.in_(student_ids),
            SkillEvaluation.status.in_(
                [SkillEvaluationStatus.VIVA_SCHEDULED, SkillEvaluationStatus.ASSIGNED]
            ),
        )
        .distinct()
        .all()
    )
    verified_count = len(verified_ids)
    viva_scheduled_count = len(viva_scheduled_ids - verified_ids)
    no_viva_count = total_students - len(verified_ids | viva_scheduled_ids)

    # DES distribution buckets: 0-25, 26-50, 51-75, 76-100
    buckets = [
        {"range": "0–25", "count": 0},
        {"range": "26–50", "count": 0},
        {"range": "51–75", "count": 0},
        {"range": "76–100", "count": 0},
    ]
    for s in students:
        score = float(s.current_des_score or 0)
        if score <= 25:
            buckets[0]["count"] += 1
        elif score <= 50:
            buckets[1]["count"] += 1
        elif score <= 75:
            buckets[2]["count"] += 1
        else:
            buckets[3]["count"] += 1

    # Top companies hiring from this college
    placed_apps = (
        db.query(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .filter(
            JobApplication.student_id.in_(student_ids),
            JobApplication.status == ApplicationStatus.SELECTED,
        )
        .all()
    )
    company_counts: dict[str, int] = {}
    for app, job in placed_apps:
        name = app.placed_by_corporate_name or job.company_name or "Unknown"
        company_counts[name] = company_counts.get(name, 0) + 1

    top_companies = [
        {"company": k, "placements": v}
        for k, v in sorted(company_counts.items(), key=lambda x: -x[1])[:10]
    ]

    return {
        "total_students": total_students,
        "placed_count": placed_count,
        "placement_rate_pct": round((placed_count / total_students) * 100, 1) if total_students else 0,
        "avg_des_score": avg_des,
        "verified_count": verified_count,
        "viva_scheduled_count": viva_scheduled_count,
        "no_viva_count": no_viva_count,
        "des_distribution": buckets,
        "top_companies": top_companies,
    }


# ── Student roster ───────────────────────────────────────────────────────────

@router.get("/students")
async def college_students(
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    """Full student roster for this college with DES + verification status."""
    college_id = str(current_user["user_id"])
    students = (
        db.query(Student)
        .filter(Student.college_id == college_id)
        .order_by(Student.current_des_score.desc())
        .all()
    )

    result = []
    for s in students:
        evals = (
            db.query(SkillEvaluation)
            .filter(SkillEvaluation.student_id == s.id)
            .all()
        )
        has_verified = any(e.status == SkillEvaluationStatus.EVALUATED for e in evals)
        has_scheduled = any(
            e.status in [SkillEvaluationStatus.VIVA_SCHEDULED, SkillEvaluationStatus.ASSIGNED]
            for e in evals
        )
        viva_status = (
            "verified" if has_verified
            else "scheduled" if has_scheduled
            else "none"
        )
        result.append({
            "student_id": str(s.id),
            "name": s.name,
            "email": s.email,
            "des_score": float(s.current_des_score or 0),
            "badge": s.badge,
            "viva_status": viva_status,
            "github_profile": s.github_profile,
            "linkedin_profile": s.linkedin_profile,
        })
    return result

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, load_only

from app.core.database import get_db
from app.core.security import get_current_college
from app.models.job import Job, JobStatus
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.resume_status import ResumeStatus
from app.models.user import College, Corporate, Mentor, SkillEvaluation, SkillEvaluationStatus, Student

router = APIRouter()


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_percent(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round((_as_float(numerator) / _as_float(denominator)) * 100, 1)


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _get_college(db: Session, current_user: dict) -> College:
    try:
        college_id = UUID(str(current_user["user_id"]))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc

    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College profile not found")
    return college


def _student_college_keys(college: College) -> list[str]:
    keys = [str(college.id)]
    if college.college_id:
        keys.append(str(college.college_id))
    return list(dict.fromkeys(keys))


def _student_scope_filter(college: College):
    return Student.college_id.in_(_student_college_keys(college))


def _job_scope_filter(college: College):
    return Job.college_id == college.id


def _profile_completion(student: Student, resume_status: ResumeStatus | None = None) -> int:
    education = student.education or []
    checks = [
        bool(student.name and student.phone and student.bio),
        any(bool(item.get("institution")) and bool(item.get("level")) for item in education if isinstance(item, dict)),
        bool(student.technical_skills),
        bool(student.soft_skills),
        bool(student.preferred_industry and student.job_roles_of_interest),
        bool(student.gender and student.country and student.state and student.city),
        bool(student.location_preferences and student.language_proficiency),
        bool(student.linkedin_profile or student.github_profile or student.personal_website),
        bool(student.resume_url or (resume_status and (resume_status.has_resume or resume_status.resume_uploaded))),
    ]
    return round((sum(1 for item in checks if item) / len(checks)) * 100)


def _department_from_student(student: Student) -> str:
    for entry in student.education or []:
        if not isinstance(entry, dict):
            continue
        for key in ("department", "branch", "specialization", "degree", "course"):
            value = entry.get(key)
            if value:
                return str(value)
    return "Unassigned"


def _year_from_student(student: Student) -> str:
    for entry in student.education or []:
        if not isinstance(entry, dict):
            continue
        for key in ("year", "graduation_year", "passing_year", "batch"):
            value = entry.get(key)
            if value:
                return str(value)
    return ""


def _project_title(student: Student, project_id: Any | None) -> str:
    projects = student.projects or []
    if not projects:
        return "Profile project"
    if project_id:
        for project in projects:
            if isinstance(project, dict) and str(project.get("id")) == str(project_id):
                return str(project.get("title") or project.get("name") or "Profile project")
    first = projects[0] if isinstance(projects[0], dict) else {}
    return str(first.get("title") or first.get("name") or "Profile project")


def _skill_domain(student: Student) -> str:
    if student.preferred_industry:
        return student.preferred_industry
    if student.job_roles_of_interest:
        return student.job_roles_of_interest
    if student.technical_skills:
        return student.technical_skills.split(",")[0].strip()
    return "General"


def _student_ids(db: Session, college: College) -> list[UUID]:
    rows = db.query(Student.id).filter(_student_scope_filter(college)).all()
    return [row[0] for row in rows]


def _resume_status_map(db: Session, student_ids: list[UUID]) -> dict[UUID, ResumeStatus]:
    if not student_ids:
        return {}
    statuses = db.query(ResumeStatus).filter(ResumeStatus.student_id.in_(student_ids)).all()
    return {item.student_id: item for item in statuses}


def _placement_status(application_statuses: list[str]) -> str:
    if ApplicationStatus.SELECTED.value in application_statuses:
        return "placed"
    if ApplicationStatus.INTERVIEW.value in application_statuses:
        return "interview"
    if ApplicationStatus.SHORTLISTED.value in application_statuses:
        return "shortlisted"
    if ApplicationStatus.APPLIED.value in application_statuses:
        return "applied"
    return "not_applied"


def _verification_status(evaluations: list[SkillEvaluation]) -> str:
    if any(item.status == SkillEvaluationStatus.EVALUATED for item in evaluations):
        return "verified"
    if any(item.status == SkillEvaluationStatus.VIVA_COMPLETED for item in evaluations):
        return "completed"
    if any(item.status == SkillEvaluationStatus.VIVA_SCHEDULED for item in evaluations):
        return "scheduled"
    if any(item.status in {SkillEvaluationStatus.SUBMITTED, SkillEvaluationStatus.ASSIGNED, SkillEvaluationStatus.UNDER_REVIEW} for item in evaluations):
        return "pending"
    return "not_started"


def _dashboard_insights(payload: dict[str, Any]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    departments = payload.get("department_analytics", [])
    verification_funnel = {item["stage"]: item["count"] for item in payload.get("verification_funnel", [])}
    placement_funnel = {item["stage"]: item["count"] for item in payload.get("placement_funnel", [])}
    mentor_analytics = payload.get("mentor_analytics", [])
    skills = payload.get("skills_demand", [])

    low_des = [item for item in departments if item.get("average_des", 0) < 50 and item.get("student_count", 0) > 0]
    if low_des:
        target = sorted(low_des, key=lambda item: item["average_des"])[0]
        insights.append({
            "type": "risk",
            "title": f"{target['department']} needs DES intervention",
            "description": f"Average DES is {target['average_des']}, below the employability threshold.",
            "metric": target["average_des"],
        })

    submitted = verification_funnel.get("Project Submitted", 0)
    scheduled = verification_funnel.get("Viva Scheduled", 0)
    if submitted > scheduled:
        insights.append({
            "type": "opportunity",
            "title": "Students are close to verification",
            "description": f"{submitted - scheduled} submitted projects still need viva scheduling.",
            "metric": submitted - scheduled,
        })

    interviewed = placement_funnel.get("Interviewed", 0)
    selected = placement_funnel.get("Selected", 0)
    if interviewed and selected / interviewed < 0.35:
        insights.append({
            "type": "bottleneck",
            "title": "Interview to selection conversion is low",
            "description": f"{selected} selections from {interviewed} interviews indicates a placement bottleneck.",
            "metric": _as_percent(selected, interviewed),
        })

    high_mentors = [item for item in mentor_analytics if item.get("average_score", 0) >= 75 and item.get("completed", 0) >= 3]
    if high_mentors:
        mentor = sorted(high_mentors, key=lambda item: item["average_score"], reverse=True)[0]
        insights.append({
            "type": "strength",
            "title": f"{mentor['mentor']} is a high-performing mentor",
            "description": f"{mentor['completed']} completed evaluations with {mentor['average_score']} average score.",
            "metric": mentor["average_score"],
        })

    if skills:
        top_skill = skills[0]
        insights.append({
            "type": "market",
            "title": f"{top_skill['skill']} is the most demanded skill",
            "description": f"It appears in {top_skill['demand']} active job requirements.",
            "metric": top_skill["demand"],
        })

    return insights[:6]


@router.get("/overview", response_model=dict)
async def get_college_overview(
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    student_ids = _student_ids(db, college)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    students = (
        db.query(Student)
        .options(
            load_only(
                Student.id,
                Student.name,
                Student.email,
                Student.college_id,
                Student.current_des_score,
                Student.education,
                Student.projects,
                Student.technical_skills,
                Student.preferred_industry,
                Student.job_roles_of_interest,
                Student.resume_url,
                Student.created_at,
            )
        )
        .filter(Student.id.in_(student_ids))
        .all()
        if student_ids
        else []
    )
    total_students = len(students)
    recent_students = sum(1 for item in students if item.created_at and item.created_at >= thirty_days_ago)
    previous_students = max(total_students - recent_students, 0)
    growth_percentage = _as_percent(recent_students, previous_students or total_students or 1)

    evaluations = (
        db.query(SkillEvaluation, Student, Mentor)
        .join(Student, Student.id == SkillEvaluation.student_id)
        .outerjoin(Mentor, Mentor.id == SkillEvaluation.mentor_id)
        .filter(SkillEvaluation.student_id.in_(student_ids))
        .all()
        if student_ids
        else []
    )
    evaluation_by_student: dict[UUID, list[SkillEvaluation]] = defaultdict(list)
    mentor_groups: dict[UUID, dict[str, Any]] = {}
    for evaluation, student, mentor in evaluations:
        evaluation_by_student[evaluation.student_id].append(evaluation)
        if mentor:
            bucket = mentor_groups.setdefault(
                mentor.id,
                {"mentor": mentor.name, "assigned": 0, "completed": 0, "pending": 0, "scores": [], "verified": 0},
            )
            bucket["assigned"] += 1
            if evaluation.status in {SkillEvaluationStatus.VIVA_COMPLETED, SkillEvaluationStatus.EVALUATED}:
                bucket["completed"] += 1
            else:
                bucket["pending"] += 1
            if evaluation.total_score is not None:
                bucket["scores"].append(evaluation.total_score)
            if evaluation.status == SkillEvaluationStatus.EVALUATED:
                bucket["verified"] += 1

    applications = (
        db.query(JobApplication, Job, Student)
        .join(Job, Job.id == JobApplication.job_id)
        .join(Student, Student.id == JobApplication.student_id)
        .filter(JobApplication.student_id.in_(student_ids))
        .all()
        if student_ids
        else []
    )
    applications_by_student: dict[UUID, list[JobApplication]] = defaultdict(list)
    for application, _job, _student in applications:
        applications_by_student[application.student_id].append(application)

    jobs = db.query(Job).filter(_job_scope_filter(college)).order_by(Job.created_at.desc()).all()

    verified_students = sum(
        1 for student in students if _verification_status(evaluation_by_student.get(student.id, [])) == "verified"
    )
    placed_students = sum(
        1
        for student in students
        if _placement_status([_enum_value(app.status) for app in applications_by_student.get(student.id, [])]) == "placed"
    )
    average_des = round(sum(_as_float(student.current_des_score) for student in students) / total_students, 1) if total_students else 0.0
    upcoming_interviews = sum(1 for app, _job, _student in applications if app.status == ApplicationStatus.INTERVIEW)
    upcoming_interviews += sum(1 for evaluation, _student, _mentor in evaluations if evaluation.status == SkillEvaluationStatus.VIVA_SCHEDULED)

    des_distribution = [
        {"bucket": "0-40", "count": sum(1 for s in students if _as_float(s.current_des_score) < 40)},
        {"bucket": "40-60", "count": sum(1 for s in students if 40 <= _as_float(s.current_des_score) < 60)},
        {"bucket": "60-75", "count": sum(1 for s in students if 60 <= _as_float(s.current_des_score) < 75)},
        {"bucket": "75-90", "count": sum(1 for s in students if 75 <= _as_float(s.current_des_score) < 90)},
        {"bucket": "90+", "count": sum(1 for s in students if _as_float(s.current_des_score) >= 90)},
    ]

    verification_funnel = [
        {"stage": "Registered", "count": total_students},
        {"stage": "Project Submitted", "count": sum(1 for s in students if bool(s.projects))},
        {"stage": "Viva Scheduled", "count": sum(1 for e, _s, _m in evaluations if e.status == SkillEvaluationStatus.VIVA_SCHEDULED)},
        {"stage": "Viva Completed", "count": sum(1 for e, _s, _m in evaluations if e.status in {SkillEvaluationStatus.VIVA_COMPLETED, SkillEvaluationStatus.EVALUATED})},
        {"stage": "Verified", "count": verified_students},
    ]

    placement_funnel = [
        {"stage": "Applied", "count": sum(1 for app, _job, _student in applications if app.status == ApplicationStatus.APPLIED)},
        {"stage": "Shortlisted", "count": sum(1 for app, _job, _student in applications if app.status == ApplicationStatus.SHORTLISTED)},
        {"stage": "Interviewed", "count": sum(1 for app, _job, _student in applications if app.status == ApplicationStatus.INTERVIEW)},
        {"stage": "Selected", "count": sum(1 for app, _job, _student in applications if app.status == ApplicationStatus.SELECTED)},
        {"stage": "Placed", "count": placed_students},
    ]

    department_groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"students": [], "verified": 0, "placed": 0})
    for student in students:
        department = _department_from_student(student)
        department_groups[department]["students"].append(student)
        if _verification_status(evaluation_by_student.get(student.id, [])) == "verified":
            department_groups[department]["verified"] += 1
        if _placement_status([_enum_value(app.status) for app in applications_by_student.get(student.id, [])]) == "placed":
            department_groups[department]["placed"] += 1

    department_analytics = []
    for department, data in department_groups.items():
        count = len(data["students"])
        department_analytics.append({
            "department": department,
            "student_count": count,
            "average_des": round(sum(_as_float(s.current_des_score) for s in data["students"]) / count, 1) if count else 0,
            "verification_percentage": _as_percent(data["verified"], count),
            "placement_percentage": _as_percent(data["placed"], count),
        })
    department_analytics.sort(key=lambda item: item["student_count"], reverse=True)

    company_groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"hired": 0, "des_scores": []})
    selected_count = 0
    for application, job, student in applications:
        if application.status != ApplicationStatus.SELECTED:
            continue
        selected_count += 1
        company = job.company_name or "Unknown company"
        company_groups[company]["hired"] += 1
        company_groups[company]["des_scores"].append(_as_float(student.current_des_score))

    top_hiring_companies = []
    for company, data in company_groups.items():
        hired = data["hired"]
        top_hiring_companies.append({
            "company": company,
            "students_hired": hired,
            "average_des": round(sum(data["des_scores"]) / hired, 1) if hired else 0,
            "placement_contribution": _as_percent(hired, selected_count),
        })
    top_hiring_companies.sort(key=lambda item: item["students_hired"], reverse=True)

    monthly_counter: Counter[str] = Counter()
    for application, _job, _student in applications:
        if application.status == ApplicationStatus.SELECTED and application.updated_at:
            monthly_counter[application.updated_at.strftime("%Y-%m")] += 1
    monthly_placement_trends = [
        {"month": month, "placements": count}
        for month, count in sorted(monthly_counter.items())[-12:]
    ]

    active_recruiter_ids = {job.corporate_id for job in jobs if job.corporate_id}
    active_recruiter_ids.update(app.corporate_id for app, _job, _student in applications if app.corporate_id)
    recruiter_count = len([item for item in active_recruiter_ids if item])

    skills_counter: Counter[str] = Counter()
    for job in jobs:
        for skill in job.skills_required or []:
            if isinstance(skill, str) and skill.strip():
                skills_counter[skill.strip()] += 1

    mentor_analytics = []
    for data in mentor_groups.values():
        assigned = data["assigned"]
        mentor_analytics.append({
            "mentor": data["mentor"],
            "assigned": assigned,
            "completed": data["completed"],
            "pending": data["pending"],
            "average_score": round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0,
            "verification_success_rate": _as_percent(data["verified"], assigned),
        })
    mentor_analytics.sort(key=lambda item: item["completed"], reverse=True)

    notifications = _build_notifications(evaluations, applications, jobs)
    payload = {
        "kpis": {
            "total_students": {"value": total_students, "growth_percentage": growth_percentage},
            "verified_students": {"value": verified_students, "verification_rate": _as_percent(verified_students, total_students)},
            "placed_students": {"value": placed_students, "placement_percentage": _as_percent(placed_students, total_students)},
            "average_des": {"value": average_des},
            "active_recruiters": {"value": recruiter_count},
            "upcoming_interviews": {"value": upcoming_interviews},
        },
        "des_distribution": des_distribution,
        "verification_funnel": verification_funnel,
        "placement_funnel": placement_funnel,
        "department_analytics": department_analytics,
        "top_hiring_companies": top_hiring_companies[:10],
        "monthly_placement_trends": monthly_placement_trends,
        "mentor_analytics": mentor_analytics,
        "skills_demand": [{"skill": skill, "demand": count} for skill, count in skills_counter.most_common(8)],
        "notifications": notifications[:12],
    }
    payload["ai_insights"] = _dashboard_insights(payload)
    return payload


@router.get("/students", response_model=dict)
async def list_college_students(
    query: str | None = Query(None),
    department: str | None = Query(None),
    year: str | None = Query(None),
    des_min: float | None = Query(None),
    des_max: float | None = Query(None),
    verified: bool | None = Query(None),
    placed: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    base_query = db.query(Student).filter(_student_scope_filter(college))
    if query:
        term = f"%{query}%"
        base_query = base_query.filter(or_(Student.name.ilike(term), Student.email.ilike(term), Student.student_unique_id.ilike(term)))
    if des_min is not None:
        base_query = base_query.filter(Student.current_des_score >= des_min)
    if des_max is not None:
        base_query = base_query.filter(Student.current_des_score <= des_max)

    all_students = base_query.order_by(Student.created_at.desc()).all()
    student_ids = [item.id for item in all_students]
    resume_map = _resume_status_map(db, student_ids)
    evaluations = db.query(SkillEvaluation).filter(SkillEvaluation.student_id.in_(student_ids)).all() if student_ids else []
    applications = db.query(JobApplication).filter(JobApplication.student_id.in_(student_ids)).all() if student_ids else []

    eval_map: dict[UUID, list[SkillEvaluation]] = defaultdict(list)
    app_map: dict[UUID, list[JobApplication]] = defaultdict(list)
    for item in evaluations:
        eval_map[item.student_id].append(item)
    for item in applications:
        app_map[item.student_id].append(item)

    rows = []
    for student in all_students:
        item_department = _department_from_student(student)
        item_year = _year_from_student(student)
        verification = _verification_status(eval_map.get(student.id, []))
        placement = _placement_status([_enum_value(app.status) for app in app_map.get(student.id, [])])
        if department and item_department != department:
            continue
        if year and item_year != year:
            continue
        if verified is not None and (verification == "verified") != verified:
            continue
        if placed is not None and (placement == "placed") != placed:
            continue
        resume_status = resume_map.get(student.id)
        rows.append({
            "id": str(student.id),
            "name": student.name,
            "roll_number": student.student_unique_id,
            "email": student.email,
            "department": item_department,
            "year": item_year,
            "des_score": _as_float(student.current_des_score),
            "ats_score": resume_status.ats_score if resume_status else None,
            "profile_completion": _profile_completion(student, resume_status),
            "verification_status": verification,
            "placement_status": placement,
        })

    total = len(rows)
    return {"data": rows[skip: skip + limit], "total": total, "skip": skip, "limit": limit, "count": len(rows[skip: skip + limit])}


@router.get("/students/{student_id}", response_model=dict)
async def get_college_student_detail(
    student_id: UUID,
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    student = db.query(Student).filter(Student.id == student_id, _student_scope_filter(college)).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    resume_status = db.query(ResumeStatus).filter(ResumeStatus.student_id == student.id).first()
    evaluations = (
        db.query(SkillEvaluation, Mentor)
        .outerjoin(Mentor, Mentor.id == SkillEvaluation.mentor_id)
        .filter(SkillEvaluation.student_id == student.id)
        .order_by(SkillEvaluation.created_at.desc())
        .all()
    )
    applications = (
        db.query(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .filter(JobApplication.student_id == student.id)
        .order_by(JobApplication.created_at.desc())
        .all()
    )

    return {
        "id": str(student.id),
        "personal_info": {
            "name": student.name,
            "email": student.email,
            "phone": student.phone,
            "dob": student.dob.isoformat() if student.dob else None,
            "gender": _enum_value(student.gender) if student.gender else None,
            "location": ", ".join(item for item in [student.city, student.state, student.country] if item),
            "bio": student.bio,
        },
        "education": student.education or [],
        "skills": {
            "technical": student.technical_skills,
            "soft": student.soft_skills,
            "certifications": student.certifications,
            "languages": student.language_proficiency,
        },
        "projects": student.projects or [],
        "links": {
            "github": student.github_profile,
            "linkedin": student.linkedin_profile,
            "live": student.personal_website,
            "resume": student.resume_url,
        },
        "scores": {
            "ats": resume_status.ats_score if resume_status else None,
            "des": _as_float(student.current_des_score),
            "profile_completion": _profile_completion(student, resume_status),
        },
        "verification_history": [
            {
                "id": str(evaluation.id),
                "project": _project_title(student, evaluation.project_id),
                "mentor": mentor.name if mentor else "Unassigned",
                "status": _enum_value(evaluation.status),
                "score": evaluation.total_score,
                "verdict": _enum_value(evaluation.verdict) if evaluation.verdict else None,
                "scheduled_date": evaluation.confirmed_slot.isoformat() if evaluation.confirmed_slot else None,
                "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
            }
            for evaluation, mentor in evaluations
        ],
        "mentor_evaluations": [
            {
                "mentor": mentor.name if mentor else "Unassigned",
                "technical": evaluation.score_technical,
                "practical": evaluation.score_practical,
                "communication": evaluation.score_communication,
                "originality": evaluation.score_originality,
                "strengths": evaluation.feedback_strengths,
                "improvements": evaluation.feedback_improvements,
            }
            for evaluation, mentor in evaluations
        ],
        "interview_history": [
            {
                "job": job.title,
                "company": job.company_name,
                "status": _enum_value(application.status),
                "date": application.updated_at.isoformat() if application.updated_at else application.created_at.isoformat(),
            }
            for application, job in applications
            if application.status in {ApplicationStatus.INTERVIEW, ApplicationStatus.SELECTED}
        ],
        "placement_history": [
            {
                "company": job.company_name,
                "role": job.title,
                "package": _as_float(job.salary_max or job.salary_min),
                "placed_date": application.updated_at.isoformat() if application.updated_at else application.created_at.isoformat(),
                "des": _as_float(student.current_des_score),
            }
            for application, job in applications
            if application.status == ApplicationStatus.SELECTED
        ],
    }


@router.get("/verification", response_model=dict)
async def get_verification_dashboard(
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    student_ids = _student_ids(db, college)
    rows = (
        db.query(SkillEvaluation, Student, Mentor)
        .join(Student, Student.id == SkillEvaluation.student_id)
        .outerjoin(Mentor, Mentor.id == SkillEvaluation.mentor_id)
        .filter(SkillEvaluation.student_id.in_(student_ids))
        .order_by(SkillEvaluation.created_at.desc())
        .all()
        if student_ids
        else []
    )
    metrics = {
        "pending_viva": sum(1 for e, _s, _m in rows if e.status in {SkillEvaluationStatus.SUBMITTED, SkillEvaluationStatus.ASSIGNED, SkillEvaluationStatus.UNDER_REVIEW}),
        "scheduled_viva": sum(1 for e, _s, _m in rows if e.status == SkillEvaluationStatus.VIVA_SCHEDULED),
        "completed_viva": sum(1 for e, _s, _m in rows if e.status in {SkillEvaluationStatus.VIVA_COMPLETED, SkillEvaluationStatus.EVALUATED}),
        "failed_viva": sum(1 for e, _s, _m in rows if e.verdict and _enum_value(e.verdict) == "did_not_pass"),
        "verified_students": len({e.student_id for e, _s, _m in rows if e.status == SkillEvaluationStatus.EVALUATED}),
    }
    mentor_buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"assigned": 0, "completed": 0, "pending": 0, "scores": [], "verified": 0})
    table = []
    for evaluation, student, mentor in rows:
        mentor_name = mentor.name if mentor else "Unassigned"
        bucket = mentor_buckets[mentor_name]
        bucket["assigned"] += 1
        if evaluation.status in {SkillEvaluationStatus.VIVA_COMPLETED, SkillEvaluationStatus.EVALUATED}:
            bucket["completed"] += 1
        else:
            bucket["pending"] += 1
        if evaluation.total_score is not None:
            bucket["scores"].append(evaluation.total_score)
        if evaluation.status == SkillEvaluationStatus.EVALUATED:
            bucket["verified"] += 1
        table.append({
            "id": str(evaluation.id),
            "student": student.name,
            "student_id": str(student.id),
            "project": _project_title(student, evaluation.project_id),
            "skill_domain": _skill_domain(student),
            "mentor": mentor_name,
            "scheduled_date": evaluation.confirmed_slot.isoformat() if evaluation.confirmed_slot else None,
            "status": _enum_value(evaluation.status),
            "score": evaluation.total_score,
            "verdict": _enum_value(evaluation.verdict) if evaluation.verdict else None,
        })
    mentor_analytics = [
        {
            "mentor": mentor,
            "assigned": data["assigned"],
            "completed": data["completed"],
            "pending": data["pending"],
            "average_score": round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0,
            "verification_success_rate": _as_percent(data["verified"], data["assigned"]),
        }
        for mentor, data in mentor_buckets.items()
    ]
    return {"metrics": metrics, "evaluations": table, "mentor_analytics": mentor_analytics}


@router.get("/placements", response_model=dict)
async def get_placements_dashboard(
    department: str | None = Query(None),
    company: str | None = Query(None),
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    student_ids = _student_ids(db, college)
    rows = (
        db.query(JobApplication, Job, Student)
        .join(Job, Job.id == JobApplication.job_id)
        .join(Student, Student.id == JobApplication.student_id)
        .filter(JobApplication.student_id.in_(student_ids))
        .order_by(JobApplication.created_at.desc())
        .all()
        if student_ids
        else []
    )
    if company:
        rows = [row for row in rows if (row[1].company_name or "") == company]
    if department:
        rows = [row for row in rows if _department_from_student(row[2]) == department]
    placed_rows = [row for row in rows if row[0].status == ApplicationStatus.SELECTED]
    packages = [_as_float(job.salary_max or job.salary_min) for _application, job, _student in placed_rows if (job.salary_max or job.salary_min)]
    offers_released = sum(1 for application, _job, _student in rows if bool(application.offer_letter))
    metrics = {
        "placement_percentage": _as_percent(len({student.id for _a, _j, student in placed_rows}), len(student_ids)),
        "average_package": round(sum(packages) / len(packages), 2) if packages else 0,
        "highest_package": max(packages) if packages else 0,
        "offers_released": offers_released,
        "offers_accepted": len(placed_rows),
    }
    feed = [
        {
            "student": student.name,
            "company": job.company_name,
            "role": job.title,
            "package": _as_float(job.salary_max or job.salary_min),
            "placed_date": application.updated_at.isoformat() if application.updated_at else application.created_at.isoformat(),
            "des": _as_float(student.current_des_score),
            "department": _department_from_student(student),
        }
        for application, job, student in placed_rows
    ]
    monthly_counter: Counter[str] = Counter()
    department_counter: Counter[str] = Counter()
    company_counter: Counter[str] = Counter()
    for application, job, student in placed_rows:
        date_value = application.updated_at or application.created_at
        monthly_counter[date_value.strftime("%Y-%m")] += 1
        department_counter[_department_from_student(student)] += 1
        company_counter[job.company_name or "Unknown company"] += 1
    return {
        "metrics": metrics,
        "feed": feed,
        "placement_trend": [{"month": key, "placements": value} for key, value in sorted(monthly_counter.items())[-12:]],
        "department_comparison": [{"department": key, "placements": value} for key, value in department_counter.most_common()],
        "company_distribution": [{"company": key, "hires": value} for key, value in company_counter.most_common(12)],
    }


@router.get("/recruiters", response_model=dict)
async def get_recruiters_dashboard(
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    student_ids = _student_ids(db, college)
    rows = (
        db.query(JobApplication, Job)
        .join(Job, Job.id == JobApplication.job_id)
        .filter(JobApplication.student_id.in_(student_ids))
        .all()
        if student_ids
        else []
    )
    jobs = db.query(Job).filter(or_(_job_scope_filter(college), Job.id.in_([row[0].job_id for row in rows]))).all()
    company_buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"jobs_posted": 0, "candidates_viewed": 0, "shortlisted": 0, "interviewed": 0, "offers_released": 0, "offers_accepted": 0})
    for job in jobs:
        company_buckets[job.company_name or "Unknown company"]["jobs_posted"] += 1
        company_buckets[job.company_name or "Unknown company"]["candidates_viewed"] += job.views_count or 0
    for application, job in rows:
        bucket = company_buckets[job.company_name or "Unknown company"]
        if application.status == ApplicationStatus.SHORTLISTED:
            bucket["shortlisted"] += 1
        if application.status == ApplicationStatus.INTERVIEW:
            bucket["interviewed"] += 1
        if application.offer_letter:
            bucket["offers_released"] += 1
        if application.status == ApplicationStatus.SELECTED:
            bucket["offers_accepted"] += 1
    table = [{"company": company, **data} for company, data in company_buckets.items()]
    metrics = {
        "active_recruiters": len(table),
        "open_jobs": sum(1 for job in jobs if job.status == JobStatus.ACTIVE),
        "shortlists": sum(item["shortlisted"] for item in table),
        "interviews": sum(item["interviewed"] for item in table),
        "offers": sum(item["offers_released"] for item in table),
    }
    return {"metrics": metrics, "recruiters": sorted(table, key=lambda item: item["jobs_posted"], reverse=True)}


@router.get("/jobs", response_model=dict)
async def get_college_jobs(
    company: str | None = Query(None),
    des_min: float | None = Query(None),
    des_max: float | None = Query(None),
    status_filter: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    query = db.query(Job).filter(_job_scope_filter(college))
    if company:
        query = query.filter(Job.company_name == company)
    if des_min is not None:
        query = query.filter(or_(Job.min_des_score == None, Job.min_des_score >= des_min))
    if des_max is not None:
        query = query.filter(or_(Job.max_des_score == None, Job.max_des_score <= des_max))
    if status_filter:
        query = query.filter(Job.status == JobStatus(status_filter))
    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    job_ids = [job.id for job in jobs]
    applications = db.query(JobApplication).filter(JobApplication.job_id.in_(job_ids)).all() if job_ids else []
    app_buckets: dict[UUID, list[JobApplication]] = defaultdict(list)
    for item in applications:
        app_buckets[item.job_id].append(item)
    data = []
    for job in jobs:
        job_apps = app_buckets.get(job.id, [])
        data.append({
            "id": str(job.id),
            "job_title": job.title,
            "company": job.company_name,
            "min_des": _as_float(job.min_des_score) if job.min_des_score is not None else None,
            "applicants": len(job_apps),
            "shortlisted": sum(1 for app in job_apps if app.status == ApplicationStatus.SHORTLISTED),
            "interviews": sum(1 for app in job_apps if app.status == ApplicationStatus.INTERVIEW),
            "selected": sum(1 for app in job_apps if app.status == ApplicationStatus.SELECTED),
            "status": _enum_value(job.status),
        })
    return {"data": data, "total": total, "skip": skip, "limit": limit, "count": len(data)}


@router.get("/notifications", response_model=dict)
async def get_college_notifications(
    type_filter: str | None = Query(None),
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    student_ids = _student_ids(db, college)
    evaluations = db.query(SkillEvaluation, Student, Mentor).join(Student, Student.id == SkillEvaluation.student_id).outerjoin(Mentor, Mentor.id == SkillEvaluation.mentor_id).filter(SkillEvaluation.student_id.in_(student_ids)).all() if student_ids else []
    applications = db.query(JobApplication, Job, Student).join(Job, Job.id == JobApplication.job_id).join(Student, Student.id == JobApplication.student_id).filter(JobApplication.student_id.in_(student_ids)).all() if student_ids else []
    jobs = db.query(Job).filter(_job_scope_filter(college)).all()
    notifications = _build_notifications(evaluations, applications, jobs)
    if type_filter:
        notifications = [item for item in notifications if item["type"] == type_filter]
    return {"unread_count": sum(1 for item in notifications if not item["read"]), "notifications": notifications}


@router.get("/reports/{report_type}")
async def download_report(
    report_type: str,
    format: str = Query("csv", pattern="^(csv|excel|pdf)$"),
    current_user: dict = Depends(get_current_college),
    db: Session = Depends(get_db),
):
    college = _get_college(db, current_user)
    if format in {"excel", "pdf"}:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=f"{format.upper()} export requires a document writer dependency. CSV is available.")
    students = db.query(Student).filter(_student_scope_filter(college)).order_by(Student.name.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["report_type", "student", "email", "department", "year", "des_score", "college"])
    for student in students:
        writer.writerow([
            report_type,
            student.name,
            student.email,
            _department_from_student(student),
            _year_from_student(student),
            _as_float(student.current_des_score),
            college.college_name,
        ])
    filename = f"{report_type}_report.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_notifications(evaluations: list[Any], applications: list[Any], jobs: list[Job]) -> list[dict[str, Any]]:
    notifications: list[dict[str, Any]] = []
    for row in evaluations:
        evaluation, student, mentor = row
        timestamp = evaluation.updated_at or evaluation.created_at
        if evaluation.status == SkillEvaluationStatus.EVALUATED:
            notifications.append({
                "id": f"verification-{evaluation.id}",
                "type": "student_verified",
                "title": "Student verified",
                "description": f"{student.name} was verified by {mentor.name if mentor else 'a mentor'}.",
                "created_at": timestamp.isoformat() if timestamp else None,
                "read": False,
            })
        elif evaluation.status == SkillEvaluationStatus.VIVA_SCHEDULED:
            notifications.append({
                "id": f"viva-{evaluation.id}",
                "type": "interview_scheduled",
                "title": "Viva scheduled",
                "description": f"{student.name} has a viva scheduled.",
                "created_at": timestamp.isoformat() if timestamp else None,
                "read": False,
            })
    for application, job, student in applications:
        timestamp = application.updated_at or application.created_at
        if application.status == ApplicationStatus.SELECTED:
            notifications.append({
                "id": f"placement-{application.id}",
                "type": "student_placed",
                "title": "Student placed",
                "description": f"{student.name} was selected for {job.title} at {job.company_name or 'a company'}.",
                "created_at": timestamp.isoformat() if timestamp else None,
                "read": False,
            })
        if application.offer_letter:
            notifications.append({
                "id": f"offer-{application.id}",
                "type": "offer_released",
                "title": "Offer released",
                "description": f"{job.company_name or 'A company'} released an offer for {student.name}.",
                "created_at": timestamp.isoformat() if timestamp else None,
                "read": False,
            })
    for job in jobs:
        if job.status == JobStatus.ACTIVE:
            notifications.append({
                "id": f"job-{job.id}",
                "type": "new_job",
                "title": "New job active",
                "description": f"{job.title} at {job.company_name or 'a recruiter'} is active.",
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "read": False,
            })
    notifications.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return notifications

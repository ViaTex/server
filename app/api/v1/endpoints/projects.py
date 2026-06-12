from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_student, get_current_user
from app.models.project import Project, ProjectStatus
from app.models.user import Mentor, SkillEvaluation, SkillEvaluationStatus, Student, UserStatus
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectStatusUpdate
from pydantic import BaseModel

router = APIRouter()


def _serialize(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        student_id=str(project.student_id),
        title=project.title,
        description=project.description,
        github_url=project.github_url,
        live_url=project.live_url,
        tech_stack=project.tech_stack or [],
        skill_domain=project.skill_domain,
        status=project.status,
        verified_badge=project.verified_badge,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# ── Student: submit project ─────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Student submits a project for mentor viva evaluation."""
    student_id = UUID(str(current_user["user_id"]))
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    project = Project(
        student_id=student_id,
        title=payload.title,
        description=payload.description,
        github_url=payload.github_url,
        live_url=payload.live_url,
        tech_stack=payload.tech_stack,
        skill_domain=payload.skill_domain,
        status=ProjectStatus.PENDING_VIVA,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Auto-assign mentor: match by skill_domain, load-balanced by fewest active evaluations.
    # Soft-fail: if no mentor found, project stays pending_viva for admin to assign manually.
    _try_auto_assign_mentor(db, project, student_id)

    return _serialize(project)


# ── Student: list own projects ───────────────────────────────────────────────

@router.get("/me", response_model=list[ProjectResponse])
async def list_my_projects(
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Student retrieves all their own project submissions."""
    student_id = UUID(str(current_user["user_id"]))
    projects = (
        db.query(Project)
        .filter(Project.student_id == student_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [_serialize(p) for p in projects]


# ── Admin: assign mentor ─────────────────────────────────────────────────────

class AssignMentorRequest(BaseModel):
    mentor_id: UUID

@router.get("/admin/unassigned", response_model=list[ProjectResponse])
async def get_unassigned_projects(
    current_admin: dict = Depends(get_current_user), # Assuming admin token
    db: Session = Depends(get_db),
):
    """Admin retrieves all projects pending mentor assignment."""
    if current_admin["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    projects = (
        db.query(Project)
        .filter(Project.status == ProjectStatus.PENDING_VIVA)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [_serialize(p) for p in projects]

# ── Public: project detail ───────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single project by ID. Accessible by mentor, corporate, and admin."""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return _serialize(project)



@router.post("/{project_id}/assign-mentor", response_model=ProjectResponse)
async def admin_assign_mentor(
    project_id: str,
    payload: AssignMentorRequest,
    current_admin: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin assigns a mentor to a project."""
    if current_admin["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProjectStatus.PENDING_VIVA:
        raise HTTPException(status_code=400, detail="Project is not pending viva assignment")

    mentor = db.query(Mentor).filter(Mentor.id == payload.mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    # Create assignment
    evaluation = SkillEvaluation(
        mentor_id=mentor.id,
        student_id=project.student_id,
        project_id=project.id,
        status=SkillEvaluationStatus.ASSIGNED,
        proposed_slots=[],
    )
    db.add(evaluation)

    project.status = ProjectStatus.VIVA_SCHEDULED
    db.commit()
    db.refresh(project)

    return _serialize(project)


# ── Mentor / Admin: update project status ───────────────────────────────────

@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: str,
    payload: ProjectStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mentor or Admin updates a project status (e.g., mark as verified or failed)."""
    if current_user["user_type"] not in {"mentor", "admin"}:
        raise HTTPException(status_code=403, detail="Only mentors or admins can update project status")

    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = payload.status
    if payload.verified_badge:
        project.verified_badge = payload.verified_badge
    elif payload.status == ProjectStatus.VERIFIED and not project.verified_badge:
        domain = project.skill_domain or "Skill"
        project.verified_badge = f"Verified {domain} Developer ✓"

    db.commit()
    db.refresh(project)
    return _serialize(project)


# ── Helper: auto-assign mentor ───────────────────────────────────────────────

def _try_auto_assign_mentor(db: Session, project: Project, student_id: UUID) -> None:
    """
    Attempt to find a best-fit mentor for the project's skill domain
    and create a SkillEvaluation record (status=assigned).
    Soft-fail: if no mentor is found, the project stays in PENDING_VIVA
    and an admin can assign manually later.
    """
    if not project.skill_domain:
        return

    domain_lower = project.skill_domain.lower()

    # Find mentors whose expertise_areas overlap with the project's skill_domain
    mentors: list[Mentor] = db.query(Mentor).filter(Mentor.status == UserStatus.ACTIVE).all()  # type: ignore[attr-defined]
    candidate_mentors = [
        m for m in mentors
        if any(domain_lower in area.lower() for area in (m.expertise_areas or []))
    ]

    if not candidate_mentors:
        # Fallback: pick any active mentor (load balanced by fewest active evaluations)
        mentors_all = db.query(Mentor).all()
        candidate_mentors = mentors_all

    if not candidate_mentors:
        return

    # Pick mentor with fewest active (non-completed) evaluations
    def active_eval_count(mentor: Mentor) -> int:
        return (
            db.query(SkillEvaluation)
            .filter(
                SkillEvaluation.mentor_id == mentor.id,
                SkillEvaluation.status.notin_(
                    [SkillEvaluationStatus.EVALUATED, SkillEvaluationStatus.VIVA_COMPLETED]
                ),
            )
            .count()
        )

    best_mentor = min(candidate_mentors, key=active_eval_count)

    evaluation = SkillEvaluation(
        mentor_id=best_mentor.id,
        student_id=student_id,
        project_id=project.id,
        status=SkillEvaluationStatus.ASSIGNED,
        proposed_slots=[],
    )
    db.add(evaluation)

    project.status = ProjectStatus.VIVA_SCHEDULED
    db.commit()

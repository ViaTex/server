from __future__ import annotations

from typing import Optional, Tuple, Any
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import SecurityManager, get_current_admin
from app.models.user import Student, Mentor, Corporate, College, UserStatus, Gender
from app.utils.helper import (
    normalize_empty,
    parse_status,
    parse_gender,
    parse_date,
    parse_float,
    parse_int,
    normalize_expertise_areas,
)

router = APIRouter()

USER_MODEL_MAP = {
    "student": Student,
    "mentor": Mentor,
    "corporate": Corporate,
    "college": College,
}

REQUIRED_FIELDS = {
    "student": {"name"},
    "mentor": {"name"},
    "corporate": {"name", "company_name"},
    "college": {"name", "college_name"},
}

ALLOWED_FIELDS = {
    "student": {
        "name",
        "phone",
        "bio",
        "dob",
        "gender",
        "country",
        "state",
        "city",
        "technical_skills",
        "soft_skills",
        "certifications",
        "preferred_industry",
        "job_roles_of_interest",
        "location_preferences",
        "language_proficiency",
        "extracurricular_activities",
        "linkedin_profile",
        "github_profile",
        "personal_website",
        "resume_url",
        "profile_picture_url",
        "current_des_score",
        "badge",
        "status",
    },
    "mentor": {
        "name",
        "phone",
        "current_role",
        "expertise_areas",
        "experience_years",
        "motivation",
        "status",
    },
    "corporate": {
        "name",
        "phone",
        "company_name",
        "contact_person",
        "contact_designation",
        "website_url",
        "industry",
        "company_size",
        "founded_year",
        "company_type",
        "description",
        "address",
        "status",
    },
    "college": {
        "name",
        "phone",
        "college_name",
        "contact_person_name",
        "contact_designation",
        "website_url",
        "institute_type",
        "established_year",
        "address",
        "courses_offered",
        "branch",
        "college_id",
        "status",
    },
}


def _get_current_admin(current_user: dict = Depends(get_current_admin)):
    if current_user.get("user_type") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user




def _normalize_user_type(user_type: Optional[str]) -> Tuple[str, Any]:
    if not user_type:
        raise HTTPException(status_code=400, detail="user_type is required")
    key = user_type.strip().lower()
    if key not in USER_MODEL_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid user_type. Must be one of: {', '.join(USER_MODEL_MAP.keys())}",
        )
    return key, USER_MODEL_MAP[key]


def _is_email_taken(db: Session, email: str) -> bool:
    for model in USER_MODEL_MAP.values():
        if db.query(model).filter(model.email == email).first():
            return True
    return False


def _resolve_user_by_id(db: Session, user_id: UUID) -> Tuple[str, Any]:
    for key, model in USER_MODEL_MAP.items():
        user = db.query(model).filter(model.id == user_id).first()
        if user:
            return key, user
    raise HTTPException(status_code=404, detail="User not found")


def _serialize_base_user(user_type: str, user) -> dict:
    return {
        "id": str(user.id),
        "user_type": user_type,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status.value if user.status else "active",
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "profile_picture_url": getattr(user, "profile_picture_url", None),
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else None,
        "last_login": user.last_login.isoformat() if getattr(user, "last_login", None) else None,
    }


def _serialize_user_list(user_type: str, user) -> dict:
    base = _serialize_base_user(user_type, user)
    if user_type == "student":
        base.update(
            {
                "bio": user.bio,
                "country": user.country,
                "state": user.state,
                "city": user.city,
                "dob": user.dob.isoformat() if user.dob else None,
                "gender": user.gender.value if user.gender else None,
            }
        )
    elif user_type == "corporate":
        base.update({"company_name": user.company_name})
    elif user_type == "college":
        base.update({"college_name": user.college_name})
    elif user_type == "mentor":
        base.update({"current_role": user.current_role})
    return base


def _serialize_user_detail(user_type: str, user) -> dict:
    base = _serialize_base_user(user_type, user)
    if user_type == "student":
        base.update(
            {
                "bio": user.bio,
                "country": user.country,
                "state": user.state,
                "city": user.city,
                "dob": user.dob.isoformat() if user.dob else None,
                "gender": user.gender.value if user.gender else None,
                "technical_skills": user.technical_skills,
                "soft_skills": user.soft_skills,
                "certifications": user.certifications,
                "preferred_industry": user.preferred_industry,
                "job_roles_of_interest": user.job_roles_of_interest,
                "location_preferences": user.location_preferences,
                "language_proficiency": user.language_proficiency,
                "extracurricular_activities": user.extracurricular_activities,
                "linkedin_profile": user.linkedin_profile,
                "github_profile": user.github_profile,
                "personal_website": user.personal_website,
                "resume_url": user.resume_url,
                "current_des_score": float(user.current_des_score) if user.current_des_score is not None else None,
                "badge": user.badge,
                "education": user.education or [],
                "experience": user.experience or [],
                "projects": user.projects or [],
                "custom_achievements": user.custom_achievements or [],
            }
        )
    elif user_type == "mentor":
        base.update(
            {
                "user_id": str(user.user_id) if user.user_id else None,
                "current_role": user.current_role,
                "expertise_areas": user.expertise_areas or [],
                "experience_years": user.experience_years,
                "motivation": user.motivation,
                "average_rating": float(user.average_rating or 0.0),
            }
        )
    elif user_type == "corporate":
        base.update(
            {
                "company_name": user.company_name,
                "contact_person": user.contact_person,
                "contact_designation": user.contact_designation,
                "website_url": user.website_url,
                "industry": user.industry,
                "company_size": user.company_size,
                "founded_year": user.founded_year,
                "company_type": user.company_type,
                "description": user.description,
                "address": user.address,
            }
        )
    elif user_type == "college":
        base.update(
            {
                "college_name": user.college_name,
                "contact_person_name": user.contact_person_name,
                "contact_designation": user.contact_designation,
                "website_url": user.website_url,
                "institute_type": user.institute_type,
                "established_year": user.established_year,
                "address": user.address,
                "courses_offered": user.courses_offered,
                "branch": user.branch,
                "college_id": user.college_id,
            }
        )
    return base


@router.get("/", response_model=dict)
async def list_users(
    user_type: str = Query("student", description="student, mentor, corporate, college"),
    query: Optional[str] = Query(None, description="Search by name, email, or phone"),
    status_filter: Optional[str] = Query(None, description="Filter by status (active, inactive, suspended, pending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db),
):
    user_key, model = _normalize_user_type(user_type)

    users_query = db.query(model)

    if query:
        search_term = f"%{query}%"
        users_query = users_query.filter(
            (model.name.ilike(search_term))
            | (model.email.ilike(search_term))
            | (model.phone.ilike(search_term))
        )

    if status_filter:
        try:
            status_enum = UserStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join([s.value for s in UserStatus])}",
            )
        users_query = users_query.filter(model.status == status_enum)

    total = users_query.count()
    users = users_query.offset(skip).limit(limit).all()
    users_data = [_serialize_user_list(user_key, item) for item in users]

    return {
        "data": users_data,
        "total": total,
        "skip": skip,
        "limit": limit,
        "count": len(users_data),
        "user_type": user_key,
    }


@router.get("/stats", response_model=dict)
async def get_user_stats(
    user_type: str = Query("student", description="student, mentor, corporate, college"),
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db),
):
    user_key, model = _normalize_user_type(user_type)

    total = db.query(model).count()
    active = db.query(model).filter(model.status == UserStatus.ACTIVE).count()
    inactive = db.query(model).filter(model.status == UserStatus.INACTIVE).count()
    suspended = db.query(model).filter(model.status == UserStatus.SUSPENDED).count()
    pending = db.query(model).filter(model.status == UserStatus.PENDING).count()
    email_verified = db.query(model).filter(model.email_verified == True).count()

    return {
        "user_type": user_key,
        "total_students": total,
        "active_students": active,
        "inactive_students": inactive,
        "suspended_students": suspended,
        "pending_students": pending,
        "email_verified": email_verified,
        "email_unverified": total - email_verified,
    }


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: str,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user_type, user = _resolve_user_by_id(db, user_uuid)
    return _serialize_user_detail(user_type, user)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: dict,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db),
):
    user_type = payload.get("user_type")
    user_key, _model = _normalize_user_type(user_type)

    email = payload.get("email")
    password = payload.get("password")
    name = payload.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if not name and user_key in ("student", "mentor"):
        raise HTTPException(status_code=400, detail="Name is required")

    if _is_email_taken(db, email):
        raise HTTPException(status_code=400, detail="Email already in use")

    status_enum = parse_status(payload.get("status"), default=UserStatus.ACTIVE)

    if user_key == "student":
        dob_value = parse_date(payload.get("dob"), "dob")
        gender_value = parse_gender(payload.get("gender"))
        current_des_score = parse_float(payload.get("current_des_score"), "current_des_score")
        if current_des_score is None:
            current_des_score = 0.0

        user = Student(
            id=uuid.uuid4(),
            name=name,
            email=email,
            password_hash=SecurityManager.get_password_hash(password),
            phone=payload.get("phone"),
            bio=payload.get("bio"),
            dob=dob_value,
            gender=gender_value,
            country=payload.get("country"),
            state=payload.get("state"),
            city=payload.get("city"),
            technical_skills=payload.get("technical_skills"),
            soft_skills=payload.get("soft_skills"),
            certifications=payload.get("certifications"),
            preferred_industry=payload.get("preferred_industry"),
            job_roles_of_interest=payload.get("job_roles_of_interest"),
            location_preferences=payload.get("location_preferences"),
            language_proficiency=payload.get("language_proficiency"),
            extracurricular_activities=payload.get("extracurricular_activities"),
            linkedin_profile=payload.get("linkedin_profile"),
            github_profile=payload.get("github_profile"),
            personal_website=payload.get("personal_website"),
            resume_url=payload.get("resume_url"),
            profile_picture_url=payload.get("profile_picture_url"),
            current_des_score=current_des_score,
            badge=payload.get("badge"),
            status=status_enum,
            email_verified=True,
        )
    elif user_key == "mentor":
        expertise_areas = normalize_expertise_areas(payload.get("expertise_areas"))
        experience_years = parse_int(payload.get("experience_years"), "experience_years")

        user = Mentor(
            id=uuid.uuid4(),
            user_id=uuid.UUID(payload.get("user_id")) if payload.get("user_id") else uuid.uuid4(),
            name=name,
            email=email,
            password_hash=SecurityManager.get_password_hash(password),
            phone=payload.get("phone"),
            current_role=payload.get("current_role"),
            expertise_areas=expertise_areas,
            experience_years=experience_years,
            motivation=payload.get("motivation"),
            status=status_enum,
            email_verified=True,
        )
    elif user_key == "corporate":
        company_name = payload.get("company_name")
        if not company_name:
            raise HTTPException(status_code=400, detail="company_name is required")
        contact_person = payload.get("contact_person")
        name_value = name or contact_person or company_name
        founded_year = parse_int(payload.get("founded_year"), "founded_year")

        user = Corporate(
            id=uuid.uuid4(),
            name=name_value,
            email=email,
            password_hash=SecurityManager.get_password_hash(password),
            phone=payload.get("phone"),
            company_name=company_name,
            contact_person=contact_person,
            contact_designation=payload.get("contact_designation"),
            website_url=payload.get("website_url"),
            industry=payload.get("industry"),
            company_size=payload.get("company_size"),
            founded_year=founded_year,
            company_type=payload.get("company_type"),
            description=payload.get("description"),
            address=payload.get("address"),
            status=status_enum,
            email_verified=True,
        )
    else:
        college_name = payload.get("college_name")
        if not college_name:
            raise HTTPException(status_code=400, detail="college_name is required")
        contact_person_name = payload.get("contact_person_name")
        name_value = name or contact_person_name or college_name
        established_year = parse_int(payload.get("established_year"), "established_year")

        user = College(
            id=uuid.uuid4(),
            name=name_value,
            email=email,
            password_hash=SecurityManager.get_password_hash(password),
            phone=payload.get("phone"),
            college_name=college_name,
            contact_person_name=contact_person_name,
            contact_designation=payload.get("contact_designation"),
            website_url=payload.get("website_url"),
            institute_type=payload.get("institute_type"),
            established_year=established_year,
            address=payload.get("address"),
            courses_offered=payload.get("courses_offered"),
            branch=payload.get("branch"),
            college_id=payload.get("college_id"),
            status=status_enum,
            email_verified=True,
        )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {**_serialize_user_detail(user_key, user), "message": "User created successfully"}


@router.patch("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    update_data: dict,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user_type, user = _resolve_user_by_id(db, user_uuid)

    if not update_data:
        raise HTTPException(status_code=400, detail="Provide an update payload")

    required_fields = REQUIRED_FIELDS.get(user_type, set())
    allowed_fields = ALLOWED_FIELDS.get(user_type, set())

    for field, value in update_data.items():
        if field not in allowed_fields:
            continue

        value = normalize_empty(value, field in required_fields, field)

        if field == "status":
            if value in (None, ""):
                continue
            value = parse_status(value, default=None)

        if field == "gender":
            if value in (None, ""):
                continue
            value = parse_gender(value)

        if field == "dob":
            value = parse_date(value, "dob")

        if field == "current_des_score":
            if value in (None, ""):
                continue
            value = parse_float(value, "current_des_score")

        if field in {"experience_years", "founded_year", "established_year"}:
            value = parse_int(value, field)

        if field == "expertise_areas":
            value = normalize_expertise_areas(value)

        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return {**_serialize_user_detail(user_type, user), "message": "User updated successfully"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user_type, user = _resolve_user_by_id(db, user_uuid)

    db.delete(user)
    db.commit()

    return None

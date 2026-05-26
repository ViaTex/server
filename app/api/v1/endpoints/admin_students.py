from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import uuid

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import Student, UserStatus
from app.schemas.student import StudentProfileResponse, StudentProfileUpdate, StudentEducation
from app.core.security import SecurityManager

router = APIRouter()


def _get_current_admin(current_user: dict = Depends(get_current_admin)):
    """Dependency to ensure admin access"""
    if current_user.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/", response_model=dict)
async def list_students(
    query: Optional[str] = Query(None, description="Search by name, email, or phone"),
    status_filter: Optional[str] = Query(None, description="Filter by status (active, inactive, suspended, pending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all students with pagination and search.
    
    **Admin Only**
    
    Features:
    - Search by name, email, or phone
    - Filter by status
    - Pagination support
    """
    try:
        students_query = db.query(Student)
        
        # Apply filters
        if query:
            search_term = f"%{query}%"
            students_query = students_query.filter(
                (Student.name.ilike(search_term)) |
                (Student.email.ilike(search_term)) |
                (Student.phone.ilike(search_term))
            )
        
        if status_filter:
            try:
                status_enum = UserStatus(status_filter)
                students_query = students_query.filter(Student.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join([s.value for s in UserStatus])}"
                )
        
        # Get total count
        total = students_query.count()
        
        # Apply pagination
        students = students_query.offset(skip).limit(limit).all()
        
        # Convert to response format
        students_data = [
            {
                "id": str(s.id),
                "name": s.name,
                "email": s.email,
                "phone": s.phone,
                "status": s.status.value if s.status else "active",
                "email_verified": s.email_verified,
                "phone_verified": s.phone_verified,
                "profile_picture_url": s.profile_picture_url,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "last_login": s.last_login.isoformat() if s.last_login else None,
                "bio": s.bio,
                "country": s.country,
                "state": s.state,
                "city": s.city,
                "dob": s.dob.isoformat() if s.dob else None,
                "gender": s.gender.value if s.gender else None,
            }
            for s in students
        ]
        
        return {
            "data": students_data,
            "total": total,
            "skip": skip,
            "limit": limit,
            "count": len(students_data)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list students: {str(e)}"
        )


@router.get("/stats", response_model=dict)
async def get_student_stats(
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get student statistics.
    
    **Admin Only**
    """
    try:
        total = db.query(Student).count()
        active = db.query(Student).filter(Student.status == UserStatus.ACTIVE).count()
        inactive = db.query(Student).filter(Student.status == UserStatus.INACTIVE).count()
        suspended = db.query(Student).filter(Student.status == UserStatus.SUSPENDED).count()
        pending = db.query(Student).filter(Student.status == UserStatus.PENDING).count()
        email_verified = db.query(Student).filter(Student.email_verified == True).count()
        
        return {
            "total_students": total,
            "active_students": active,
            "inactive_students": inactive,
            "suspended_students": suspended,
            "pending_students": pending,
            "email_verified": email_verified,
            "email_unverified": total - email_verified
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get student stats: {str(e)}"
        )


@router.get("/{student_id}", response_model=dict)
async def get_student(
    student_id: str,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get a specific student's details.
    
    **Admin Only**
    """
    try:
        student_uuid = UUID(student_id)
        student = db.query(Student).filter(Student.id == student_uuid).first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        return {
            "id": str(student.id),
            "name": student.name,
            "email": student.email,
            "phone": student.phone,
            "status": student.status.value if student.status else "active",
            "email_verified": student.email_verified,
            "phone_verified": student.phone_verified,
            "profile_picture_url": student.profile_picture_url,
            "created_at": student.created_at.isoformat() if student.created_at else None,
            "updated_at": student.updated_at.isoformat() if student.updated_at else None,
            "last_login": student.last_login.isoformat() if student.last_login else None,
            "bio": student.bio,
            "country": student.country,
            "state": student.state,
            "city": student.city,
            "dob": student.dob.isoformat() if student.dob else None,
            "gender": student.gender.value if student.gender else None,
            "technical_skills": student.technical_skills,
            "soft_skills": student.soft_skills,
            "certifications": student.certifications,
            "preferred_industry": student.preferred_industry,
            "job_roles_of_interest": student.job_roles_of_interest,
            "location_preferences": student.location_preferences,
            "language_proficiency": student.language_proficiency,
            "extracurricular_activities": student.extracurricular_activities,
            "education": student.education or [],
            "experience": student.experience or [],
            "projects": student.projects or [],
            "custom_achievements": student.custom_achievements or [],
        }
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get student: {str(e)}"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: dict,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new student account.
    
    **Admin Only**
    
    Required fields:
    - name: Student's full name
    - email: Unique email address
    - password: Password for the account (min 8 characters)
    
    Optional fields:
    - phone: Contact number
    - dob: Date of birth (YYYY-MM-DD)
    - gender: male, female, or other
    - bio: Short biography
    - country, state, city: Location information
    - technical_skills: Comma-separated technical skills
    - preferred_industry: Preferred industry
    """
    try:
        # Validate required fields
        if not student_data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name is required"
            )
        if not student_data.get("email"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        if not student_data.get("password"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )
        
        # Check if password is strong enough
        if len(student_data["password"]) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Check if email already exists
        existing_student = db.query(Student).filter(
            Student.email == student_data["email"]
        ).first()
        
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        
        # Create new student
        password_hash = SecurityManager.get_password_hash(student_data["password"])
        
        new_student = Student(
            id=uuid.uuid4(),
            name=student_data.get("name"),
            email=student_data.get("email"),
            password_hash=password_hash,
            phone=student_data.get("phone"),
            bio=student_data.get("bio"),
            gender=student_data.get("gender"),
            country=student_data.get("country"),
            state=student_data.get("state"),
            city=student_data.get("city"),
            dob=student_data.get("dob"),
            technical_skills=student_data.get("technical_skills"),
            soft_skills=student_data.get("soft_skills"),
            certifications=student_data.get("certifications"),
            preferred_industry=student_data.get("preferred_industry"),
            job_roles_of_interest=student_data.get("job_roles_of_interest"),
            location_preferences=student_data.get("location_preferences"),
            language_proficiency=student_data.get("language_proficiency"),
            extracurricular_activities=student_data.get("extracurricular_activities"),
            status=UserStatus.ACTIVE,
            email_verified=True,  # Admins create pre-verified accounts
        )
        
        db.add(new_student)
        db.commit()
        db.refresh(new_student)
        
        return {
            "id": str(new_student.id),
            "name": new_student.name,
            "email": new_student.email,
            "phone": new_student.phone,
            "status": new_student.status.value,
            "email_verified": new_student.email_verified,
            "created_at": new_student.created_at.isoformat() if new_student.created_at else None,
            "message": "Student created successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create student: {str(e)}"
        )


@router.patch("/{student_id}", response_model=dict)
async def update_student(
    student_id: str,
    update_data: dict,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update student information.
    
    **Admin Only**
    
    Can update any student field. Fields not provided will not be changed.
    """
    try:
        student_uuid = UUID(student_id)
        student = db.query(Student).filter(Student.id == student_uuid).first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Update allowed fields
        allowed_fields = {
            "name", "phone", "bio", "gender", "country", "state", "city",
            "dob", "technical_skills", "soft_skills", "certifications",
            "preferred_industry", "job_roles_of_interest", "location_preferences",
            "language_proficiency", "extracurricular_activities", "status"
        }
        
        for field, value in update_data.items():
            if field not in allowed_fields:
                continue
            
            if field == "status":
                try:
                    value = UserStatus(value)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status. Must be one of: {', '.join([s.value for s in UserStatus])}"
                    )
            
            setattr(student, field, value)
        
        db.commit()
        db.refresh(student)
        
        return {
            "id": str(student.id),
            "name": student.name,
            "email": student.email,
            "phone": student.phone,
            "status": student.status.value if student.status else "active",
            "email_verified": student.email_verified,
            "updated_at": student.updated_at.isoformat() if student.updated_at else None,
            "message": "Student updated successfully"
        }
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update student: {str(e)}"
        )


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a student account.
    
    **Admin Only**
    
    Note: This will permanently delete the student account and all associated data.
    """
    try:
        student_uuid = UUID(student_id)
        student = db.query(Student).filter(Student.id == student_uuid).first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        db.delete(student)
        db.commit()
        
        return None
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete student: {str(e)}"
        )


@router.get("/", response_model=dict)
async def get_student_statistics(
    current_admin: dict = Depends(_get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get student statistics and analytics.
    
    **Admin Only**
    """
    try:
        total_students = db.query(Student).count()
        active_students = db.query(Student).filter(
            Student.status == UserStatus.ACTIVE
        ).count()
        inactive_students = db.query(Student).filter(
            Student.status == UserStatus.INACTIVE
        ).count()
        suspended_students = db.query(Student).filter(
            Student.status == UserStatus.SUSPENDED
        ).count()
        pending_students = db.query(Student).filter(
            Student.status == UserStatus.PENDING
        ).count()
        
        email_verified = db.query(Student).filter(
            Student.email_verified == True
        ).count()
        
        return {
            "total_students": total_students,
            "active_students": active_students,
            "inactive_students": inactive_students,
            "suspended_students": suspended_students,
            "pending_students": pending_students,
            "email_verified": email_verified,
            "email_unverified": total_students - email_verified
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get student statistics: {str(e)}"
        )

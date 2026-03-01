"""Student Profile API Endpoints"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user, allow_student
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.student import (
    StudentProfileWizardRequest,
    StudentProfileUpdateRequest,
    StudentProfileResponse,
    StudentProfileSummaryResponse,
    ProfileCompletionStatusResponse,
    ProjectDeleteResponse,
    AddSkillRequest,
    AddProjectRequest,
    AddEducationRequest,
    UpdateBioRequest,
    MessageResponse
)
from app.services.student_service import StudentProfileService

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/profile/wizard",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or Update Student Profile (Wizard)",
    description="""
    Unified upsert endpoint for the profile wizard.
    
    **Features:**
    - Creates a new profile if one doesn't exist
    - Updates existing profile with provided data
    - Supports both manual JSON input and AI-generated draft data
    - Validates mandatory fields ONLY when `is_draft=False`
    
    **Mandatory Fields (for final save):**
    - date_of_birth
    - gender
    - location (city, state, country)
    - education (minimum 1 entry)
    - skills (minimum 3 skills)
    
    **Draft Mode:**
    Set `is_draft=True` to save progress without validation.
    """
)
async def create_or_update_profile_wizard(
    profile_data: StudentProfileWizardRequest,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update student profile using the wizard flow.
    Validates mandatory fields only when is_draft=False.
    """
    profile = await StudentProfileService.upsert_profile_wizard(
        db=db,
        user_id=current_user.id,
        data=profile_data
    )
    
    logger.info(
        "Profile wizard upsert",
        user_id=str(current_user.id),
        is_draft=profile.is_draft,
        is_complete=profile.is_complete
    )
    
    return profile


@router.patch(
    "/profile",
    response_model=StudentProfileResponse,
    summary="Partial Profile Update",
    description="""
    Update specific fields of an existing profile.
    
    **Usage:**
    - Only provide fields you want to update
    - Omitted fields remain unchanged
    - Arrays (education, skills, projects) replace existing data when provided
    - Location fields are merged with existing data
    """
)
async def update_profile_partial(
    update_data: StudentProfileUpdateRequest,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Partial update for specific profile fields.
    """
    profile = await StudentProfileService.update_profile_partial(
        db=db,
        user_id=current_user.id,
        data=update_data
    )
    
    return profile


@router.delete(
    "/profile/projects/{project_id}",
    response_model=ProjectDeleteResponse,
    summary="Delete a Project",
    description="Remove a specific project from the student's profile by project ID."
)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific project from the student's profile.
    """
    success, remaining_count = await StudentProfileService.delete_project(
        db=db,
        user_id=current_user.id,
        project_id=project_id
    )
    
    return ProjectDeleteResponse(
        message="Project deleted successfully",
        deleted_project_id=project_id,
        remaining_projects_count=remaining_count
    )


@router.get(
    "/profile/me",
    response_model=StudentProfileResponse,
    summary="Get My Profile",
    description="""
    Retrieve the full student profile for the authenticated user.
    
    Returns all profile data including:
    - Personal information (DOB, gender, location)
    - Education history
    - Skills
    - Projects
    - AI-generated or manually edited bio
    - Profile completion status
    """
)
async def get_my_profile(
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current student's full profile.
    """
    profile = await StudentProfileService.get_profile_by_user_id(
        db=db,
        user_id=current_user.id
    )
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create a profile using the wizard."
        )
    
    return profile


@router.get(
    "/profile/completion-status",
    response_model=ProfileCompletionStatusResponse,
    summary="Get Profile Completion Status",
    description="Check profile completion status and see which mandatory fields are missing."
)
async def get_completion_status(
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Get profile completion status and missing fields.
    """
    return await StudentProfileService.get_completion_status(
        db=db,
        user_id=current_user.id
    )


@router.post(
    "/profile/finalize",
    response_model=StudentProfileResponse,
    summary="Finalize Profile",
    description="""
    Convert a draft profile to a finalized profile.
    
    **Requirements:**
    - All mandatory fields must be complete
    - Profile must currently be in draft state
    
    **Effect:**
    - Sets is_draft=False
    - Sets is_complete=True (if all validations pass)
    """
)
async def finalize_profile(
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalize a draft profile after completing all mandatory fields.
    """
    profile = await StudentProfileService.finalize_profile(
        db=db,
        user_id=current_user.id
    )
    
    return profile


@router.post(
    "/profile/skills",
    response_model=StudentProfileResponse,
    summary="Add a Skill",
    description="Add a single skill to the student's profile."
)
async def add_skill(
    skill_data: AddSkillRequest,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a single skill to the profile.
    """
    skill_dict = skill_data.skill.model_dump()
    profile = await StudentProfileService.add_skill(
        db=db,
        user_id=current_user.id,
        skill_data=skill_dict
    )
    
    return profile


@router.post(
    "/profile/projects",
    response_model=StudentProfileResponse,
    summary="Add a Project",
    description="Add a single project to the student's profile. A unique project ID will be auto-generated."
)
async def add_project(
    project_data: AddProjectRequest,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a single project to the profile.
    """
    project_dict = project_data.project.model_dump()
    # Convert links to dict if it's a Pydantic model
    if project_dict.get('links') and hasattr(project_dict['links'], 'model_dump'):
        project_dict['links'] = project_dict['links'].model_dump()
    
    profile = await StudentProfileService.add_project(
        db=db,
        user_id=current_user.id,
        project_data=project_dict
    )
    
    return profile


@router.post(
    "/profile/education",
    response_model=StudentProfileResponse,
    summary="Add Education Entry",
    description="Add a single education entry to the student's profile."
)
async def add_education(
    education_data: AddEducationRequest,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a single education entry to the profile.
    """
    education_dict = education_data.education.model_dump()
    profile = await StudentProfileService.add_education(
        db=db,
        user_id=current_user.id,
        education_data=education_dict
    )
    
    return profile


@router.patch(
    "/profile/bio",
    response_model=StudentProfileResponse,
    summary="Update Bio",
    description="""
    Update the student's bio.
    
    **AI Bio Support:**
    - Set `is_ai_generated=True` when saving AI-generated bio
    - If the user edits an AI-generated bio, the system tracks this automatically
    """
)
async def update_bio(
    bio_data: UpdateBioRequest,
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the student's bio.
    """
    profile = await StudentProfileService.update_bio(
        db=db,
        user_id=current_user.id,
        bio=bio_data.bio,
        is_ai_generated=bio_data.is_ai_generated
    )
    
    return profile


@router.get(
    "/profile/summary",
    response_model=StudentProfileSummaryResponse,
    summary="Get Profile Summary",
    description="Get a lightweight summary of the student profile (useful for dashboards)."
)
async def get_profile_summary(
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a lightweight summary of the student profile.
    """
    profile = await StudentProfileService.get_profile_by_user_id(
        db=db,
        user_id=current_user.id
    )
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return StudentProfileSummaryResponse(
        id=profile.id,
        user_id=profile.user_id,
        is_complete=profile.is_complete,
        is_draft=profile.is_draft,
        completion_percentage=profile.completion_percentage,
        has_bio=profile.bio is not None and len(profile.bio) > 0,
        skill_count=len(profile.skills) if profile.skills else 0,
        project_count=len(profile.projects) if profile.projects else 0,
        education_count=len(profile.education) if profile.education else 0
    )


@router.delete(
    "/profile",
    response_model=MessageResponse,
    summary="Delete Profile",
    description="Permanently delete the student's profile."
)
async def delete_profile(
    current_user: User = Depends(allow_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete the student's profile.
    """
    await StudentProfileService.delete_profile(
        db=db,
        user_id=current_user.id
    )
    
    return MessageResponse(
        message="Profile deleted successfully",
        detail="Your student profile has been permanently removed."
    )

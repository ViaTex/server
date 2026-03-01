"""Student Profile Service Layer"""

from datetime import datetime, timezone
from typing import Optional, Tuple, List
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from app.models.student_info import StudentInfo
from app.models.user import User
from app.schemas.student import (
    StudentProfileWizardRequest,
    StudentProfileUpdateRequest,
    StudentProfileResponse,
    ProfileCompletionStatusResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class StudentProfileService:
    """Service for student profile operations"""
    
    @staticmethod
    async def get_profile_by_user_id(
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[StudentInfo]:
        """Get student profile by user ID"""
        stmt = select(StudentInfo).where(StudentInfo.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_or_create_profile(
        db: AsyncSession,
        user_id: UUID
    ) -> Tuple[StudentInfo, bool]:
        """
        Get existing profile or create a new draft profile.
        Returns (profile, was_created)
        """
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if profile:
            return profile, False
        
        # Create new draft profile
        profile = StudentInfo(
            user_id=user_id,
            is_draft=True,
            is_complete=False,
            completion_percentage=0
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
        logger.info("Created new student profile", user_id=str(user_id), profile_id=str(profile.id))
        return profile, True
    
    @staticmethod
    async def upsert_profile_wizard(
        db: AsyncSession,
        user_id: UUID,
        data: StudentProfileWizardRequest
    ) -> StudentInfo:
        """
        Unified upsert for profile wizard.
        Handles both manual JSON input and AI-generated draft data.
        Validates mandatory fields only when is_draft=False.
        """
        profile, was_created = await StudentProfileService.get_or_create_profile(db, user_id)
        
        # Update basic fields
        if data.date_of_birth is not None:
            profile.date_of_birth = data.date_of_birth
        if data.gender is not None:
            profile.gender = data.gender
        
        # Update location (convert Pydantic model to dict)
        if data.location is not None:
            profile.location = data.location.model_dump() if hasattr(data.location, 'model_dump') else dict(data.location)
        
        # Update education array
        if data.education is not None:
            profile.education = [
                edu.model_dump() if hasattr(edu, 'model_dump') else dict(edu) 
                for edu in data.education
            ]
        
        # Update skills array
        if data.skills is not None:
            profile.skills = [
                skill.model_dump() if hasattr(skill, 'model_dump') else dict(skill) 
                for skill in data.skills
            ]
        
        # Update projects array (assign UUIDs to projects without IDs)
        if data.projects is not None:
            projects_list = []
            for proj in data.projects:
                proj_dict = proj.model_dump() if hasattr(proj, 'model_dump') else dict(proj)
                if proj_dict.get('id') is None:
                    proj_dict['id'] = str(uuid4())
                elif isinstance(proj_dict.get('id'), UUID):
                    proj_dict['id'] = str(proj_dict['id'])
                # Convert links to dict if exists
                if proj_dict.get('links') and hasattr(proj_dict['links'], 'model_dump'):
                    proj_dict['links'] = proj_dict['links'].model_dump()
                projects_list.append(proj_dict)
            profile.projects = projects_list
        
        # Update bio
        if data.bio is not None:
            # Track if AI bio was edited
            if profile.bio_is_ai_generated and profile.bio and profile.bio != data.bio:
                profile.bio_is_edited = True
            profile.bio = data.bio
            profile.bio_is_ai_generated = data.bio_is_ai_generated
        
        # Update draft status
        profile.is_draft = data.is_draft
        
        # Calculate completion percentage
        profile.completion_percentage = profile.calculate_completion_percentage()
        
        # Check if profile is complete
        is_complete, _ = profile.check_mandatory_fields_complete()
        profile.is_complete = is_complete and not data.is_draft
        
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        logger.info(
            "Updated student profile",
            user_id=str(user_id),
            profile_id=str(profile.id),
            is_draft=profile.is_draft,
            is_complete=profile.is_complete,
            completion_percentage=profile.completion_percentage
        )
        
        return profile
    
    @staticmethod
    async def update_profile_partial(
        db: AsyncSession,
        user_id: UUID,
        data: StudentProfileUpdateRequest
    ) -> StudentInfo:
        """
        Partial update for specific fields.
        Only updates provided fields.
        """
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found. Please create a profile first using the wizard."
            )
        
        # Update only provided fields
        if data.date_of_birth is not None:
            profile.date_of_birth = data.date_of_birth
        
        if data.gender is not None:
            profile.gender = data.gender
        
        if data.location is not None:
            # Merge with existing location
            existing_location = profile.location or {}
            location_update = data.location.model_dump(exclude_none=True) if hasattr(data.location, 'model_dump') else {k: v for k, v in data.location.items() if v is not None}
            existing_location.update(location_update)
            profile.location = existing_location
        
        if data.education is not None:
            profile.education = [
                edu.model_dump() if hasattr(edu, 'model_dump') else dict(edu) 
                for edu in data.education
            ]
        
        if data.skills is not None:
            profile.skills = [
                skill.model_dump() if hasattr(skill, 'model_dump') else dict(skill) 
                for skill in data.skills
            ]
        
        if data.projects is not None:
            projects_list = []
            for proj in data.projects:
                proj_dict = proj.model_dump() if hasattr(proj, 'model_dump') else dict(proj)
                if proj_dict.get('id') is None:
                    proj_dict['id'] = str(uuid4())
                elif isinstance(proj_dict.get('id'), UUID):
                    proj_dict['id'] = str(proj_dict['id'])
                projects_list.append(proj_dict)
            profile.projects = projects_list
        
        if data.bio is not None:
            if profile.bio_is_ai_generated and profile.bio and profile.bio != data.bio:
                profile.bio_is_edited = True
            profile.bio = data.bio
        
        if data.bio_is_ai_generated is not None:
            profile.bio_is_ai_generated = data.bio_is_ai_generated
        
        # Recalculate completion
        profile.completion_percentage = profile.calculate_completion_percentage()
        is_complete, _ = profile.check_mandatory_fields_complete()
        profile.is_complete = is_complete and not profile.is_draft
        
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        logger.info(
            "Partially updated student profile",
            user_id=str(user_id),
            profile_id=str(profile.id)
        )
        
        return profile
    
    @staticmethod
    async def delete_project(
        db: AsyncSession,
        user_id: UUID,
        project_id: UUID
    ) -> Tuple[bool, int]:
        """
        Delete a specific project from the profile.
        Returns (success, remaining_projects_count)
        """
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        if not profile.projects:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No projects found in profile"
            )
        
        # Find and remove the project
        project_id_str = str(project_id)
        original_count = len(profile.projects)
        profile.projects = [
            p for p in profile.projects 
            if str(p.get('id')) != project_id_str
        ]
        
        if len(profile.projects) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        logger.info(
            "Deleted project from profile",
            user_id=str(user_id),
            project_id=project_id_str,
            remaining_count=len(profile.projects)
        )
        
        return True, len(profile.projects)
    
    @staticmethod
    async def add_skill(
        db: AsyncSession,
        user_id: UUID,
        skill_data: dict
    ) -> StudentInfo:
        """Add a single skill to the profile"""
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        skills = profile.skills or []
        skills.append(skill_data)
        profile.skills = skills
        
        profile.completion_percentage = profile.calculate_completion_percentage()
        is_complete, _ = profile.check_mandatory_fields_complete()
        profile.is_complete = is_complete and not profile.is_draft
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        return profile
    
    @staticmethod
    async def add_project(
        db: AsyncSession,
        user_id: UUID,
        project_data: dict
    ) -> StudentInfo:
        """Add a single project to the profile"""
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        # Assign UUID if not provided
        if not project_data.get('id'):
            project_data['id'] = str(uuid4())
        
        projects = profile.projects or []
        projects.append(project_data)
        profile.projects = projects
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        return profile
    
    @staticmethod
    async def add_education(
        db: AsyncSession,
        user_id: UUID,
        education_data: dict
    ) -> StudentInfo:
        """Add a single education entry to the profile"""
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        education = profile.education or []
        education.append(education_data)
        profile.education = education
        
        profile.completion_percentage = profile.calculate_completion_percentage()
        is_complete, _ = profile.check_mandatory_fields_complete()
        profile.is_complete = is_complete and not profile.is_draft
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        return profile
    
    @staticmethod
    async def update_bio(
        db: AsyncSession,
        user_id: UUID,
        bio: str,
        is_ai_generated: bool = False
    ) -> StudentInfo:
        """Update bio field"""
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        # Track if AI bio was edited
        if profile.bio_is_ai_generated and profile.bio and profile.bio != bio:
            profile.bio_is_edited = True
        
        profile.bio = bio
        profile.bio_is_ai_generated = is_ai_generated
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        return profile
    
    @staticmethod
    async def get_completion_status(
        db: AsyncSession,
        user_id: UUID
    ) -> ProfileCompletionStatusResponse:
        """Get profile completion status"""
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            return ProfileCompletionStatusResponse(
                is_complete=False,
                completion_percentage=0,
                missing_fields=[
                    "date_of_birth",
                    "gender",
                    "location",
                    "education (minimum 1 entry required)",
                    "skills (minimum 3 skills required)"
                ]
            )
        
        is_complete, missing_fields = profile.check_mandatory_fields_complete()
        
        return ProfileCompletionStatusResponse(
            is_complete=is_complete and not profile.is_draft,
            completion_percentage=profile.completion_percentage,
            missing_fields=missing_fields
        )
    
    @staticmethod
    async def finalize_profile(
        db: AsyncSession,
        user_id: UUID
    ) -> StudentInfo:
        """
        Finalize a draft profile.
        Validates all mandatory fields and marks profile as complete.
        """
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        is_complete, missing_fields = profile.check_mandatory_fields_complete()
        
        if not is_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot finalize profile. Missing mandatory fields: {', '.join(missing_fields)}"
            )
        
        profile.is_draft = False
        profile.is_complete = True
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(profile)
        
        logger.info(
            "Finalized student profile",
            user_id=str(user_id),
            profile_id=str(profile.id)
        )
        
        return profile
    
    @staticmethod
    async def delete_profile(
        db: AsyncSession,
        user_id: UUID
    ) -> bool:
        """Delete student profile (soft delete could be implemented)"""
        profile = await StudentProfileService.get_profile_by_user_id(db, user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found"
            )
        
        await db.delete(profile)
        await db.commit()
        
        logger.info(
            "Deleted student profile",
            user_id=str(user_id)
        )
        
        return True

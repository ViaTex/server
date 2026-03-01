"""Schemas module initialization"""
from app.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    TokenResponse,
    OTPVerifyRequest,
    OTPResendRequest,
    OTPVerifyResponse,
    TokenRefreshResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    LogoutResponse,
    UserResponse
)
from app.schemas.student import (
    LocationSchema,
    LocationUpdateSchema,
    EducationSchema,
    SkillSchema,
    ProjectSchema,
    ProjectLinksSchema,
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
    MessageResponse as StudentMessageResponse
)

__all__ = [
    # Auth schemas
    "UserRegisterRequest",
    "UserRegisterResponse",
    "UserLoginRequest",
    "TokenResponse",
    "OTPVerifyRequest",
    "OTPResendRequest",
    "OTPVerifyResponse",
    "TokenRefreshResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "LogoutResponse",
    "UserResponse",
    # Student schemas
    "LocationSchema",
    "LocationUpdateSchema",
    "EducationSchema",
    "SkillSchema",
    "ProjectSchema",
    "ProjectLinksSchema",
    "StudentProfileWizardRequest",
    "StudentProfileUpdateRequest",
    "StudentProfileResponse",
    "StudentProfileSummaryResponse",
    "ProfileCompletionStatusResponse",
    "ProjectDeleteResponse",
    "AddSkillRequest",
    "AddProjectRequest",
    "AddEducationRequest",
    "UpdateBioRequest"
]

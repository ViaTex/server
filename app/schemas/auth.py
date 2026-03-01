from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ============= User Registration =============

class UserRegisterRequest(BaseModel):
    """Request schema for user registration"""
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)
    account_type: str = Field(..., pattern="^(Individual|Institutional)$")
    role: str = Field(..., pattern="^(Student|Mentor|TPO|Corporate HR)$")
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove common phone number characters
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?[1-9]\d{9,14}$', cleaned):
            raise ValueError("Invalid phone number format")
        return cleaned
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserRegisterResponse(BaseModel):
    """Response schema for user registration"""
    user_id: UUID
    email: str
    phone_number: str
    message: str = "Registration successful. Please verify your email and phone."
    
    model_config = {"from_attributes": True}


# ============= User Login =============

class UserLoginRequest(BaseModel):
    """Request schema for user login"""
    email: EmailStr
    password: str


# ============= User Response =============

class UserResponse(BaseModel):
    """Response schema for user information"""
    id: UUID
    email: str
    phone_number: str
    account_type: str
    role: str
    email_verified: bool
    phone_verified: bool
    account_status: str
    last_login_at: Optional[datetime]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response schema for JWT tokens"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


# ============= OTP Verification =============

class OTPVerifyRequest(BaseModel):
    """Request schema for OTP verification"""
    user_id: UUID
    email_otp: str = Field(..., min_length=6, max_length=6)
    phone_otp: str = Field(..., min_length=6, max_length=6)


class OTPResendRequest(BaseModel):
    """Request schema for OTP resend"""
    user_id: UUID
    type: str = Field(..., pattern="^(email|phone|both)$")


class OTPVerifyResponse(BaseModel):
    """Response schema for OTP verification"""
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"


# ============= OAuth =============

class OAuthCallbackRequest(BaseModel):
    """Request schema for OAuth callback"""
    code: str
    state: Optional[str] = None


class OAuthPhoneVerifyRequest(BaseModel):
    """Request schema for OAuth phone verification (new users)"""
    user_id: UUID
    phone_number: str = Field(..., min_length=10, max_length=20)
    account_type: str = Field(..., pattern="^(Individual|Institutional)$")
    role: str = Field(..., pattern="^(Student|Mentor|TPO|Corporate HR)$")


# ============= Token Refresh =============

class TokenRefreshResponse(BaseModel):
    """Response schema for token refresh"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============= Password Reset =============

class PasswordResetRequest(BaseModel):
    """Request schema for password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request schema for password reset confirmation"""
    user_id: UUID
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v


# ============= Logout =============

class LogoutResponse(BaseModel):
    """Response schema for logout"""
    message: str = "Logged out successfully"


# ============= Generic Responses =============

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    detail: Optional[str] = None

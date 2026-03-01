from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
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
    MessageResponse,
    UserResponse
)
from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.services.email_service import EmailService
from app.services.sms_service import SMSService

router = APIRouter()
logger = get_logger(__name__)


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and phone number.
    Sends OTP to both email and phone for verification.
    """
    user, email_otp, phone_otp = await AuthService.register_user(db, register_data)
    
    return UserRegisterResponse(
        user_id=user.id,
        email=user.email,
        phone_number=user.phone_number,
        message="Registration successful. Please verify your email and phone with the OTPs sent."
    )


@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    verify_data: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify both email and phone OTPs to activate account.
    Returns access token upon successful verification.
    """
    user = await AuthService.verify_dual_otp(
        db,
        verify_data.user_id,
        verify_data.email_otp,
        verify_data.phone_otp
    )
    
    # Generate tokens
    from app.core.security import create_access_token
    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "account_type": user.account_type,
        "role": user.role
    })
    
    return OTPVerifyResponse(
        success=True,
        message="Account verified and activated successfully",
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    resend_data: OTPResendRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resend OTP for email or phone verification"""
    from sqlalchemy import select
    
    # Get user
    stmt = select(User).where(User.id == resend_data.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    messages = []
    
    # Resend email OTP
    if resend_data.type in ["email", "both"]:
        email_otp = await OTPService.create_otp(db, user.id, "email_verify")
        await EmailService.send_otp_email(user.email, email_otp.otp_code)
        messages.append("Email OTP sent")
    
    # Resend phone OTP
    if resend_data.type in ["phone", "both"]:
        phone_otp = await OTPService.create_otp(db, user.id, "phone_verify")
        await SMSService.send_otp_sms(user.phone_number, phone_otp.otp_code)
        messages.append("Phone OTP sent")
    
    return MessageResponse(
        message=" and ".join(messages),
        detail="Please check your email and/or phone for the verification code"
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    request: Request,
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    Returns access token and sets refresh token as HttpOnly cookie.
    """
    # Get client info
    device_ip = request.client.host
    user_agent = request.headers.get("user-agent")
    
    # Authenticate user
    access_token, refresh_token, user = await AuthService.login_user(
        db,
        login_data,
        device_ip,
        user_agent
    )
    
    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,  # True in production with HTTPS
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 30 days in seconds
        domain=settings.COOKIE_DOMAIN
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token from HttpOnly cookie.
    Returns a new access token.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    access_token, user = await AuthService.refresh_access_token(db, refresh_token)
    
    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Logout user by revoking refresh token and clearing cookie.
    """
    if refresh_token:
        await AuthService.logout_user(db, refresh_token)
    
    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        domain=settings.COOKIE_DOMAIN
    )
    
    return LogoutResponse(message="Logged out successfully")


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset - sends OTP to email"""
    from sqlalchemy import select
    
    # Get user
    stmt = select(User).where(User.email == reset_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if email exists
        return MessageResponse(
            message="If the email exists, a password reset code has been sent",
            detail="Please check your email for the reset code"
        )
    
    # Generate OTP
    otp = await OTPService.create_otp(db, user.id, "password_reset")
    await EmailService.send_password_reset_email(user.email, otp.otp_code)
    
    return MessageResponse(
        message="Password reset code sent to your email",
        detail="Please check your email for the reset code"
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with OTP and set new password"""
    from sqlalchemy import select
    from app.core.security import hash_password
    
    # Verify OTP
    success, error = await OTPService.verify_otp(
        db,
        reset_data.user_id,
        reset_data.otp_code,
        "password_reset"
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Get user and update password
    stmt = select(User).where(User.id == reset_data.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password_hash = hash_password(reset_data.new_password)
    await db.commit()
    
    logger.info("Password reset successful", user_id=str(user.id))
    
    return MessageResponse(
        message="Password reset successful",
        detail="You can now login with your new password"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user information"""
    return UserResponse.model_validate(current_user)


# Example protected endpoint demonstrating role-based access
@router.get("/protected/student")
async def student_only_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    """Example endpoint accessible only by Students"""
    from app.core.security import RoleChecker
    
    role_checker = RoleChecker(["Student"])
    role_checker(current_user)
    
    return {
        "message": "Welcome, Student!",
        "user_id": str(current_user.id),
        "email": current_user.email
    }


@router.get("/protected/staff")
async def staff_only_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    """Example endpoint accessible by TPO, Corporate HR, and Mentor"""
    from app.core.security import RoleChecker
    
    role_checker = RoleChecker(["TPO", "Corporate HR", "Mentor"])
    role_checker(current_user)
    
    return {
        "message": "Welcome, Staff member!",
        "user_id": str(current_user.id),
        "role": current_user.role
    }

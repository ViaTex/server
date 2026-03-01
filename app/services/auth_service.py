from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status

from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.core.secure_logging import get_secure_logger, log_auth_event, log_security_event
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.services.otp_service import OTPService
from app.services.email_service import EmailService
from app.services.sms_service import SMSService

logger = get_secure_logger(__name__)


class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    async def register_user(
        db: AsyncSession,
        register_data: UserRegisterRequest
    ) -> Tuple[User, str, str]:
        """
        Register a new user and send verification OTPs
        
        Returns:
            Tuple of (user, email_otp, phone_otp)
        """
        # Check if email already exists
        stmt = select(User).where(User.email == register_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if phone already exists
        stmt = select(User).where(User.phone_number == register_data.phone_number)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Create user
        user = User(
            email=register_data.email,
            phone_number=register_data.phone_number,
            password_hash=hash_password(register_data.password),
            account_type=register_data.account_type,
            role=register_data.role,
            email_verified=False,
            phone_verified=False,
            account_status="pending"
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Secure logging - email is automatically masked in production
        log_auth_event(
            logger,
            "User registered",
            user_id=str(user.id),
            email=user.email,  # Will be masked: r***@gmail.com
            role=user.role,
            account_type=user.account_type
        )
        
        # Generate OTPs
        email_otp_obj = await OTPService.create_otp(db, user.id, "email_verify")
        phone_otp_obj = await OTPService.create_otp(db, user.id, "phone_verify")
        
        # Send OTPs
        await EmailService.send_otp_email(user.email, email_otp_obj.otp_code)
        await SMSService.send_otp_sms(user.phone_number, phone_otp_obj.otp_code)
        
        return user, email_otp_obj.otp_code, phone_otp_obj.otp_code
    
    @staticmethod
    async def verify_dual_otp(
        db: AsyncSession,
        user_id: UUID,
        email_otp: str,
        phone_otp: str
    ) -> User:
        """Verify both email and phone OTPs to activate account"""
        
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify email OTP
        email_success, email_error = await OTPService.verify_otp(
            db, user_id, email_otp, "email_verify"
        )
        
        if not email_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email verification failed: {email_error}"
            )
        
        # Verify phone OTP
        phone_success, phone_error = await OTPService.verify_otp(
            db, user_id, phone_otp, "phone_verify"
        )
        
        if not phone_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phone verification failed: {phone_error}"
            )
        
        # Update user status
        user.email_verified = True
        user.phone_verified = True
        user.account_status = "active"
        
        await db.commit()
        await db.refresh(user)
        
        log_auth_event(logger, "User account activated", user_id=str(user.id))
        
        return user
    
    @staticmethod
    async def login_user(
        db: AsyncSession,
        login_data: UserLoginRequest,
        device_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str, User]:
        """
        Authenticate user and create session
        
        Returns:
            Tuple of (access_token, refresh_token, user)
        """
        # Get user by email
        stmt = select(User).where(User.email == login_data.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = (user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked. Try again in {int(remaining)} minutes."
            )
        
        # Verify password
        if not user.password_hash or not verify_password(login_data.password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if max attempts reached
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                await db.commit()
                
                # Security event - no PII logged
                log_security_event(
                    logger,
                    "Account locked due to failed login attempts",
                    user_id=str(user.id),
                    attempts=user.failed_login_attempts,
                    lockout_minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account locked due to too many failed attempts. Try again in {settings.ACCOUNT_LOCKOUT_MINUTES} minutes."
                )
            
            await db.commit()
            
            remaining = settings.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect email or password. {remaining} attempts remaining."
            )
        
        # Check if account is active
        if user.account_status != "active":
            # Resend OTPs so the user can verify
            try:
                email_otp_obj = await OTPService.create_otp(db, user.id, "email_verify")
                phone_otp_obj = await OTPService.create_otp(db, user.id, "phone_verify")
                await EmailService.send_otp_email(user.email, email_otp_obj.otp_code)
                await SMSService.send_otp_sms(user.phone_number, phone_otp_obj.otp_code)
            except Exception:
                pass  # Best-effort OTP resend
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Account is not active. Please complete email and phone verification.",
                    "user_id": str(user.id),
                    "email": user.email,
                    "requires_verification": True
                }
            )
        
        # Reset failed attempts and update last login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        
        # Create tokens
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "account_type": user.account_type,
            "role": user.role
        })
        
        refresh_token_str = create_refresh_token(str(user.id))
        
        # Store refresh token
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            device_ip=device_ip,
            user_agent=user_agent
        )
        
        db.add(refresh_token)
        await db.commit()
        await db.refresh(user)
        
        # Secure logging - email masked, token never logged
        log_auth_event(
            logger,
            "User logged in",
            user_id=str(user.id),
            email=user.email,  # Masked in production
            account_type=user.account_type,
            role=user.role
        )
        
        return access_token, refresh_token_str, user
    
    @staticmethod
    async def logout_user(db: AsyncSession, refresh_token: str) -> bool:
        """Revoke refresh token on logout"""
        
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if token:
            token.is_revoked = True
            token.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            
            log_auth_event(logger, "User logged out", user_id=str(token.user_id))
            return True
        
        return False
    
    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Tuple[str, User]:
        """Generate new access token from refresh token"""
        
        # Find refresh token
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token or not token.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user
        stmt = select(User).where(User.id == token.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is not active"
            )
        
        # Create new access token
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "account_type": user.account_type,
            "role": user.role
        })
        
        log_auth_event(logger, "Access token refreshed", user_id=str(user.id))
        
        return access_token, user

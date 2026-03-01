from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from app.models.otp import OTP
from app.models.user import User
from app.core.config import settings
from app.core.secure_logging import get_secure_logger, log_auth_event

logger = get_secure_logger(__name__)


class OTPService:
    """Service for handling OTP generation, storage, and verification"""
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random numeric OTP"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    @staticmethod
    async def create_otp(
        db: AsyncSession,
        user_id: UUID,
        otp_type: str,
        expire_minutes: Optional[int] = None
    ) -> OTP:
        """
        Create and store an OTP for a user
        
        Args:
            db: Database session
            user_id: User UUID
            otp_type: Type of OTP (email_verify, phone_verify, password_reset)
            expire_minutes: Expiration time in minutes (default from settings)
        
        Returns:
            OTP object
        """
        # Delete any existing unused OTPs of the same type for this user
        await db.execute(
            delete(OTP).where(
                OTP.user_id == user_id,
                OTP.type == otp_type,
                OTP.used == False
            )
        )
        
        # Generate OTP code
        otp_code = OTPService.generate_otp(settings.OTP_LENGTH)
        
        # Calculate expiration
        if expire_minutes is None:
            expire_minutes = settings.OTP_EXPIRE_MINUTES
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
        
        # Create OTP record
        otp = OTP(
            user_id=user_id,
            otp_code=otp_code,
            type=otp_type,
            expires_at=expires_at,
            used=False,
            attempts=0
        )
        
        db.add(otp)
        await db.commit()
        await db.refresh(otp)
        
        logger.info(
            "OTP created",
            user_id=str(user_id),
            otp_type=otp_type,
            expires_at=expires_at.isoformat()
        )
        
        return otp
    
    @staticmethod
    async def verify_otp(
        db: AsyncSession,
        user_id: UUID,
        otp_code: str,
        otp_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        Verify an OTP code
        
        Args:
            db: Database session
            user_id: User UUID
            otp_code: OTP code to verify
            otp_type: Type of OTP
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Find the OTP
        stmt = select(OTP).where(
            OTP.user_id == user_id,
            OTP.type == otp_type,
            OTP.used == False
        ).order_by(OTP.created_at.desc())
        
        result = await db.execute(stmt)
        otp = result.scalar_one_or_none()
        
        if not otp:
            return False, "OTP not found or already used"
        
        # Check if expired
        if otp.is_expired:
            logger.warning("OTP expired", user_id=str(user_id), otp_type=otp_type)
            return False, "OTP has expired. Please request a new one."
        
        # Check max attempts
        if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            logger.warning("OTP max attempts exceeded", user_id=str(user_id), otp_type=otp_type)
            return False, "Maximum verification attempts exceeded. Please request a new OTP."
        
        # Increment attempts
        otp.attempts += 1
        
        # Verify the code
        if otp.otp_code != otp_code:
            await db.commit()
            remaining = settings.OTP_MAX_ATTEMPTS - otp.attempts
            logger.warning(
                "OTP verification failed",
                user_id=str(user_id),
                otp_type=otp_type,
                attempts=otp.attempts
            )
            return False, f"Invalid OTP code. {remaining} attempts remaining."
        
        # Mark as used
        otp.used = True
        otp.used_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info("OTP verified successfully", user_id=str(user_id), otp_type=otp_type)
        return True, None
    
    @staticmethod
    async def cleanup_expired_otps(db: AsyncSession) -> int:
        """
        Delete expired OTPs from database
        
        Returns:
            Number of deleted OTPs
        """
        result = await db.execute(
            delete(OTP).where(OTP.expires_at < datetime.now(timezone.utc))
        )
        await db.commit()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info("Expired OTPs cleaned up", count=deleted_count)
        
        return deleted_count

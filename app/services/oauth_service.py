from typing import Optional, Tuple, Dict, Any
from uuid import UUID
import httpx
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.oauth_connection import OAuthConnection
from app.core.config import settings
from app.core.secure_logging import get_secure_logger, log_auth_event
from app.services.otp_service import OTPService
from app.services.sms_service import SMSService

logger = get_secure_logger(__name__)

# Initialize OAuth
oauth = OAuth()

# Register Google OAuth
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Register LinkedIn OAuth
oauth.register(
    name='linkedin',
    client_id=settings.LINKEDIN_CLIENT_ID,
    client_secret=settings.LINKEDIN_CLIENT_SECRET,
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    client_kwargs={'scope': 'r_liteprofile r_emailaddress'}
)


class OAuthService:
    """Service for OAuth authentication"""
    
    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from Google OAuth"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Failed to get Google user info", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Google"
            )
    
    @staticmethod
    async def get_linkedin_user_info(access_token: str) -> Dict[str, Any]:
        """Get user info from LinkedIn OAuth"""
        try:
            async with httpx.AsyncClient() as client:
                # Get profile
                profile_response = await client.get(
                    'https://api.linkedin.com/v2/me',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                profile_response.raise_for_status()
                profile_data = profile_response.json()
                
                # Get email
                email_response = await client.get(
                    'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                email_response.raise_for_status()
                email_data = email_response.json()
                
                # Combine data
                return {
                    'id': profile_data.get('id'),
                    'firstName': profile_data.get('localizedFirstName'),
                    'lastName': profile_data.get('localizedLastName'),
                    'email': email_data.get('elements', [{}])[0].get('handle~', {}).get('emailAddress')
                }
                
        except Exception as e:
            logger.error("Failed to get LinkedIn user info", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from LinkedIn"
            )
    
    @staticmethod
    async def handle_oauth_login(
        db: AsyncSession,
        provider: str,
        provider_id: str,
        provider_email: str,
        provider_name: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> Tuple[User, bool]:
        """
        Handle OAuth login/registration
        
        Returns:
            Tuple of (user, is_new_user)
        """
        # Check if OAuth connection exists
        stmt = select(OAuthConnection).where(
            OAuthConnection.provider == provider,
            OAuthConnection.provider_id == provider_id
        )
        result = await db.execute(stmt)
        oauth_conn = result.scalar_one_or_none()
        
        if oauth_conn:
            # Existing OAuth connection - login
            stmt = select(User).where(User.id == oauth_conn.user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User account not found"
                )
            
            logger.info(
                "OAuth login",
                provider=provider,
                user_id=str(user.id),
                email=user.email
            )
            
            return user, False
        
        # Check if user with this email exists
        stmt = select(User).where(User.email == provider_email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Link OAuth to existing user
            oauth_conn = OAuthConnection(
                user_id=existing_user.id,
                provider=provider,
                provider_id=provider_id,
                provider_email=provider_email,
                provider_name=provider_name,
                access_token=access_token
            )
            db.add(oauth_conn)
            
            # Auto-verify email since OAuth provider guarantees it
            existing_user.email_verified = True
            
            await db.commit()
            await db.refresh(existing_user)
            
            logger.info(
                "OAuth linked to existing user",
                provider=provider,
                user_id=str(existing_user.id)
            )
            
            return existing_user, False
        
        # Create new user (will need phone verification)
        # Note: OAuth users don't have passwords initially
        user = User(
            email=provider_email,
            phone_number="",  # Will be set during phone verification
            password_hash=None,  # OAuth-only users don't have passwords
            account_type="",  # Will be set during phone verification
            role="",  # Will be set during phone verification
            email_verified=True,  # Auto-verified via OAuth
            phone_verified=False,
            account_status="pending"  # Will be activated after phone verification
        )
        
        db.add(user)
        await db.flush()  # Get user.id
        
        # Create OAuth connection
        oauth_conn = OAuthConnection(
            user_id=user.id,
            provider=provider,
            provider_id=provider_id,
            provider_email=provider_email,
            provider_name=provider_name,
            access_token=access_token
        )
        db.add(oauth_conn)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(
            "New OAuth user created",
            provider=provider,
            user_id=str(user.id),
            email=user.email
        )
        
        return user, True
    
    @staticmethod
    async def complete_oauth_registration(
        db: AsyncSession,
        user_id: UUID,
        phone_number: str,
        account_type: str,
        role: str
    ) -> Tuple[User, str]:
        """
        Complete OAuth user registration by adding phone and role
        
        Returns:
            Tuple of (user, phone_otp)
        """
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if phone already exists
        stmt = select(User).where(
            User.phone_number == phone_number,
            User.id != user_id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Update user
        user.phone_number = phone_number
        user.account_type = account_type
        user.role = role
        
        await db.commit()
        await db.refresh(user)
        
        # Generate and send phone OTP
        phone_otp_obj = await OTPService.create_otp(db, user.id, "phone_verify")
        await SMSService.send_otp_sms(user.phone_number, phone_otp_obj.otp_code)
        
        logger.info(
            "OAuth registration completed - phone verification pending",
            user_id=str(user.id)
        )
        
        return user, phone_otp_obj.otp_code
    
    @staticmethod
    async def verify_oauth_phone(
        db: AsyncSession,
        user_id: UUID,
        phone_otp: str
    ) -> User:
        """Verify phone for OAuth user and activate account"""
        
        # Verify phone OTP
        success, error = await OTPService.verify_otp(
            db, user_id, phone_otp, "phone_verify"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phone verification failed: {error}"
            )
        
        # Get and update user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.phone_verified = True
        user.account_status = "active"
        
        await db.commit()
        await db.refresh(user)
        
        logger.info("OAuth user account activated", user_id=str(user.id))
        
        return user

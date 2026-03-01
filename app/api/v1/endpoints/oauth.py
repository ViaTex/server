from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request as StarletteRequest

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.auth import (
    OAuthPhoneVerifyRequest,
    TokenResponse,
    UserResponse,
    MessageResponse
)
from app.services.oauth_service import OAuthService, oauth
from app.services.otp_service import OTPService

router = APIRouter()
logger = get_logger(__name__)


# ============= Google OAuth =============

@router.get("/google/login")
async def google_login(request: StarletteRequest):
    """Redirect to Google OAuth login"""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: StarletteRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    
    If user exists: Login and set tokens
    If new user: Create user with email verified, prompt for phone verification
    """
    try:
        # Get access token from Google
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info
        user_info = await OAuthService.get_google_user_info(token['access_token'])
        
        # Extract user data
        provider_id = user_info.get('id')
        provider_email = user_info.get('email')
        provider_name = user_info.get('name')
        
        if not provider_id or not provider_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Google"
            )
        
        # Handle OAuth login/registration
        user, is_new_user = await OAuthService.handle_oauth_login(
            db=db,
            provider="google",
            provider_id=provider_id,
            provider_email=provider_email,
            provider_name=provider_name,
            access_token=token.get('access_token')
        )
        
        # If new user or phone not verified, redirect to phone verification
        if is_new_user or not user.phone_verified:
            # Return user_id for phone verification step
            return {
                "status": "phone_verification_required",
                "user_id": str(user.id),
                "email": user.email,
                "message": "Please provide your phone number, account type, and role to complete registration"
            }
        
        # Existing user - create session
        access_token_str = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "account_type": user.account_type,
            "role": user.role
        })
        
        refresh_token_str = create_refresh_token(str(user.id))
        
        # Store refresh token
        from app.models.refresh_token import RefreshToken
        from datetime import datetime
        
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            device_ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        db.add(refresh_token_obj)
        await db.commit()
        
        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            domain=settings.COOKIE_DOMAIN
        )
        
        logger.info("Google OAuth login successful", user_id=str(user.id))
        
        return TokenResponse(
            access_token=access_token_str,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except Exception as e:
        logger.error("Google OAuth error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth authentication failed: {str(e)}"
        )


# ============= LinkedIn OAuth =============

@router.get("/linkedin/login")
async def linkedin_login(request: StarletteRequest):
    """Redirect to LinkedIn OAuth login"""
    redirect_uri = settings.LINKEDIN_REDIRECT_URI
    return await oauth.linkedin.authorize_redirect(request, redirect_uri)


@router.get("/linkedin/callback")
async def linkedin_callback(
    request: StarletteRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle LinkedIn OAuth callback.
    
    If user exists: Login and set tokens
    If new user: Create user with email verified, prompt for phone verification
    """
    try:
        # Get access token from LinkedIn
        token = await oauth.linkedin.authorize_access_token(request)
        
        # Get user info
        user_info = await OAuthService.get_linkedin_user_info(token['access_token'])
        
        # Extract user data
        provider_id = user_info.get('id')
        provider_email = user_info.get('email')
        provider_name = f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip()
        
        if not provider_id or not provider_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from LinkedIn"
            )
        
        # Handle OAuth login/registration
        user, is_new_user = await OAuthService.handle_oauth_login(
            db=db,
            provider="linkedin",
            provider_id=provider_id,
            provider_email=provider_email,
            provider_name=provider_name,
            access_token=token.get('access_token')
        )
        
        # If new user or phone not verified, redirect to phone verification
        if is_new_user or not user.phone_verified:
            return {
                "status": "phone_verification_required",
                "user_id": str(user.id),
                "email": user.email,
                "message": "Please provide your phone number, account type, and role to complete registration"
            }
        
        # Existing user - create session
        access_token_str = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "account_type": user.account_type,
            "role": user.role
        })
        
        refresh_token_str = create_refresh_token(str(user.id))
        
        # Store refresh token
        from app.models.refresh_token import RefreshToken
        from datetime import datetime
        
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            device_ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        db.add(refresh_token_obj)
        await db.commit()
        
        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token_str,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            domain=settings.COOKIE_DOMAIN
        )
        
        logger.info("LinkedIn OAuth login successful", user_id=str(user.id))
        
        return TokenResponse(
            access_token=access_token_str,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except Exception as e:
        logger.error("LinkedIn OAuth error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LinkedIn OAuth authentication failed: {str(e)}"
        )


# ============= Complete OAuth Registration =============

@router.post("/complete-registration", response_model=MessageResponse)
async def complete_oauth_registration(
    phone_data: OAuthPhoneVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete OAuth registration by providing phone number, account type, and role.
    Sends OTP to phone for verification.
    """
    user, phone_otp = await OAuthService.complete_oauth_registration(
        db=db,
        user_id=phone_data.user_id,
        phone_number=phone_data.phone_number,
        account_type=phone_data.account_type,
        role=phone_data.role
    )
    
    return MessageResponse(
        message="Phone OTP sent",
        detail=f"Please verify your phone number with the OTP sent to {user.phone_number}"
    )


@router.post("/verify-phone", response_model=TokenResponse)
async def verify_oauth_phone(
    response: Response,
    request: Request,
    user_id: str,
    phone_otp: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify phone OTP for OAuth user.
    Activates account and returns tokens.
    """
    from uuid import UUID
    
    user = await OAuthService.verify_oauth_phone(
        db=db,
        user_id=UUID(user_id),
        phone_otp=phone_otp
    )
    
    # Create session
    access_token_str = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "account_type": user.account_type,
        "role": user.role
    })
    
    refresh_token_str = create_refresh_token(str(user.id))
    
    # Store refresh token
    from app.models.refresh_token import RefreshToken
    from datetime import datetime
    
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        device_ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(refresh_token_obj)
    await db.commit()
    
    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        domain=settings.COOKIE_DOMAIN
    )
    
    logger.info("OAuth phone verification successful", user_id=str(user.id))
    
    return TokenResponse(
        access_token=access_token_str,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )

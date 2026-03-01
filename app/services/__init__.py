"""Services module initialization"""
from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.services.email_service import EmailService
from app.services.sms_service import SMSService
from app.services.oauth_service import OAuthService
from app.services.student_service import StudentProfileService

__all__ = [
    "AuthService",
    "OTPService",
    "EmailService",
    "SMSService",
    "OAuthService",
    "StudentProfileService"
]

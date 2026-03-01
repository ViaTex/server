import aiosmtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings
from app.core.secure_logging import get_secure_logger

logger = get_secure_logger(__name__)


class EmailService:
    """Service for sending emails via ZeptoMail"""
    
    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        timeout: int = 10
    ) -> bool:
        """
        Send an email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
            timeout: Timeout in seconds (default: 10)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = subject
            
            # Attach plain text
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Attach HTML if provided
            if html:
                html_part = MIMEText(html, "html")
                message.attach(html_part)
            
            # Send email with timeout
            await asyncio.wait_for(
                aiosmtplib.send(
                    message,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    username=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    use_tls=True,
                ),
                timeout=timeout
            )
            
            logger.info("Email sent successfully", to_email=to_email, subject=subject)
            return True
            
        except Exception as e:
            logger.error("Failed to send email", to_email=to_email, error=str(e))
            return False
    
    @staticmethod
    async def send_otp_email(to_email: str, otp_code: str, user_name: Optional[str] = None) -> bool:
        """
        Send OTP verification email
        
        Args:
            to_email: Recipient email address
            otp_code: OTP code to send
            user_name: Optional user name for personalization
        
        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"Your {settings.APP_NAME} Verification Code"
        
        # Plain text version
        body = f"""
Hello{' ' + user_name if user_name else ''},

Your verification code is: {otp_code}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request this code, please ignore this email.

Best regards,
{settings.APP_NAME} Team
        """.strip()
        
        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4F46E5; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 30px; }}
        .otp-code {{ 
            font-size: 32px; 
            font-weight: bold; 
            color: #4F46E5; 
            text-align: center; 
            letter-spacing: 5px;
            padding: 20px;
            background-color: white;
            border: 2px dashed #4F46E5;
            margin: 20px 0;
        }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{settings.APP_NAME}</h1>
        </div>
        <div class="content">
            <h2>Email Verification</h2>
            <p>Hello{' ' + user_name if user_name else ''},</p>
            <p>Your verification code is:</p>
            <div class="otp-code">{otp_code}</div>
            <p><strong>This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.</strong></p>
            <p>If you didn't request this code, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>© 2026 {settings.APP_NAME}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return await EmailService.send_email(to_email, subject, body, html)
    
    @staticmethod
    async def send_password_reset_email(
        to_email: str, 
        otp_code: str, 
        user_name: Optional[str] = None
    ) -> bool:
        """Send password reset OTP email"""
        subject = f"Password Reset - {settings.APP_NAME}"
        
        body = f"""
Hello{' ' + user_name if user_name else ''},

You requested to reset your password. Your verification code is: {otp_code}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request a password reset, please ignore this email and ensure your account is secure.

Best regards,
{settings.APP_NAME} Team
        """.strip()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #DC2626; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 30px; }}
        .otp-code {{ 
            font-size: 32px; 
            font-weight: bold; 
            color: #DC2626; 
            text-align: center; 
            letter-spacing: 5px;
            padding: 20px;
            background-color: white;
            border: 2px dashed #DC2626;
            margin: 20px 0;
        }}
        .warning {{ background-color: #FEF3C7; padding: 15px; border-left: 4px solid #F59E0B; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset</h1>
        </div>
        <div class="content">
            <p>Hello{' ' + user_name if user_name else ''},</p>
            <p>You requested to reset your password. Your verification code is:</p>
            <div class="otp-code">{otp_code}</div>
            <p><strong>This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.</strong></p>
            <div class="warning">
                <strong>⚠️ Security Notice:</strong><br>
                If you didn't request a password reset, please ignore this email and ensure your account is secure.
            </div>
        </div>
        <div class="footer">
            <p>© 2026 {settings.APP_NAME}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return await EmailService.send_email(to_email, subject, body, html)

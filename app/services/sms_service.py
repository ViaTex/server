import httpx
import asyncio
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SMSService:
    """Service for sending SMS messages"""
    
    @staticmethod
    async def send_sms(to_phone: str, message: str, timeout: int = 10) -> bool:
        """
        Send SMS message
        
        Args:
            to_phone: Recipient phone number
            message: SMS message content
            timeout: Timeout in seconds (default: 10)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # This is a generic implementation
            # Replace with your SMS provider's API
            
            if settings.SMS_PROVIDER.lower() == "twilio":
                return await asyncio.wait_for(
                    SMSService._send_via_twilio(to_phone, message),
                    timeout=timeout
                )
            elif settings.SMS_PROVIDER.lower() == "aws_sns":
                return await asyncio.wait_for(
                    SMSService._send_via_aws_sns(to_phone, message),
                    timeout=timeout
                )
            else:
                logger.error("Unsupported SMS provider", provider=settings.SMS_PROVIDER)
                return False
        
        except asyncio.TimeoutError:
            logger.error("SMS send timeout", to_phone=to_phone)
            return False        
        except Exception as e:
            logger.error("Failed to send SMS", to_phone=to_phone, error=str(e))
            return False
    
    @staticmethod
    async def _send_via_twilio(to_phone: str, message: str) -> bool:
        """Send SMS via Twilio"""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.SMS_API_KEY}/Messages.json"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    auth=(settings.SMS_API_KEY, settings.SMS_API_SECRET),
                    data={
                        "From": settings.SMS_FROM_NUMBER,
                        "To": to_phone,
                        "Body": message
                    }
                )
                
                if response.status_code == 201:
                    logger.info("SMS sent via Twilio", to_phone=to_phone)
                    return True
                else:
                    logger.error(
                        "Twilio API error",
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False
                    
        except Exception as e:
            logger.error("Twilio SMS error", error=str(e))
            return False
    
    @staticmethod
    async def _send_via_aws_sns(to_phone: str, message: str) -> bool:
        """Send SMS via AWS SNS"""
        try:
            import boto3
            
            sns_client = boto3.client(
                'sns',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            response = sns_client.publish(
                PhoneNumber=to_phone,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                logger.info("SMS sent via AWS SNS", to_phone=to_phone)
                return True
            else:
                logger.error("AWS SNS error", response=response)
                return False
                
        except Exception as e:
            logger.error("AWS SNS SMS error", error=str(e))
            return False
    
    @staticmethod
    async def send_otp_sms(to_phone: str, otp_code: str) -> bool:
        """
        Send OTP verification SMS
        
        Args:
            to_phone: Recipient phone number
            otp_code: OTP code to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = f"Your {settings.APP_NAME} verification code is: {otp_code}. Valid for {settings.OTP_EXPIRE_MINUTES} minutes."
        return await SMSService.send_sms(to_phone, message)
    
    @staticmethod
    async def send_password_reset_sms(to_phone: str, otp_code: str) -> bool:
        """Send password reset OTP SMS"""
        message = f"Your {settings.APP_NAME} password reset code is: {otp_code}. Valid for {settings.OTP_EXPIRE_MINUTES} minutes. If you didn't request this, please ignore."
        return await SMSService.send_sms(to_phone, message)

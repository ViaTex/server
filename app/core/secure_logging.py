"""
Production-grade secure logging utilities for FastAPI
Prevents logging of sensitive PII data
"""
import re
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging import get_logger as _get_base_logger


def mask_email(email: str) -> str:
    """
    Mask email address for security
    Example: rahul.bastia@gmail.com -> r***@gmail.com
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email string
    """
    if not email or '@' not in email:
        return "***"
    
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = f"{local[0]}***"
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number for security
    Example: +916371480952 -> +91****0952
    
    Args:
        phone: Phone number to mask
        
    Returns:
        Masked phone string
    """
    if not phone:
        return "***"
    
    # Keep first 3 and last 4 digits, mask the rest
    if len(phone) > 7:
        return f"{phone[:3]}****{phone[-4:]}"
    else:
        return "***"


def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize dictionary data for secure logging
    Masks or removes sensitive fields based on environment
    
    Args:
        data: Dictionary containing log data
        
    Returns:
        Sanitized dictionary safe for logging
    """
    if settings.APP_ENV == "production":
        # In production, remove ALL PII
        sensitive_keys = {
            'email', 'to_email', 'from_email', 'user_email',
            'phone', 'phone_number', 'to_phone', 'mobile',
            'password', 'password_hash', 'passwd',
            'token', 'access_token', 'refresh_token', 'auth_token',
            'otp', 'otp_code', 'verification_code',
            'jwt', 'secret', 'api_key', 'secret_key',
            'credit_card', 'card_number', 'ssn', 'social_security'
        }
        
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    elif settings.APP_ENV == "development":
        # In development, mask PII but keep it partially visible
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                key_lower = key.lower()
                if 'email' in key_lower:  # Handles email, to_email, from_email, user_email
                    sanitized[key] = mask_email(value)
                elif 'phone' in key_lower or 'mobile' in key_lower:  # Handles phone, phone_number, mobile
                    sanitized[key] = mask_phone(value)
                elif key_lower in ('password', 'password_hash', 'passwd', 'token', 'access_token', 
                                   'refresh_token', 'auth_token', 'otp_code', 'verification_code',
                                   'jwt', 'secret', 'api_key', 'secret_key'):
                    sanitized[key] = "[MASKED]"
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    else:  # staging or other environments
        # Similar to production but more lenient
        return sanitize_for_logging({**data, '__env__': 'staging'})


class SecureLogger:
    """
    Secure logger wrapper that automatically sanitizes sensitive data
    """
    
    def __init__(self, logger_name: str):
        self._logger = _get_base_logger(logger_name)
        self._is_production = settings.APP_ENV == "production"
        self._is_development = settings.APP_ENV == "development"
    
    def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize keyword arguments before logging"""
        return sanitize_for_logging(kwargs)
    
    def info(self, event: str, **kwargs):
        """Log info level with automatic PII sanitization"""
        sanitized = self._sanitize_kwargs(kwargs)
        self._logger.info(event, **sanitized)
    
    def warning(self, event: str, **kwargs):
        """Log warning level with automatic PII sanitization"""
        sanitized = self._sanitize_kwargs(kwargs)
        self._logger.warning(event, **sanitized)
    
    def error(self, event: str, **kwargs):
        """Log error level with automatic PII sanitization"""
        sanitized = self._sanitize_kwargs(kwargs)
        self._logger.error(event, **sanitized)
    
    def debug(self, event: str, **kwargs):
        """Log debug level with automatic PII sanitization"""
        if self._is_development:
            sanitized = self._sanitize_kwargs(kwargs)
            self._logger.debug(event, **sanitized)
    
    def critical(self, event: str, **kwargs):
        """Log critical level with automatic PII sanitization"""
        sanitized = self._sanitize_kwargs(kwargs)
        # In critical logs, we still sanitize but add a marker
        sanitized['_severity'] = 'CRITICAL'
        self._logger.error(event, **sanitized)


def get_secure_logger(name: str) -> SecureLogger:
    """
    Get a secure logger instance that automatically sanitizes PII
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        SecureLogger instance
    """
    return SecureLogger(name)


# Convenience functions for common logging patterns
def log_auth_event(logger: SecureLogger, event: str, user_id: str, **extra):
    """
    Log authentication event with secure defaults
    
    Args:
        logger: SecureLogger instance
        event: Event description
        user_id: User ID (safe to log)
        **extra: Additional context (will be sanitized)
    """
    logger.info(
        event,
        user_id=user_id,
        event_type="auth",
        **extra
    )


def log_user_action(logger: SecureLogger, action: str, user_id: str, **extra):
    """
    Log user action with secure defaults
    
    Args:
        logger: SecureLogger instance
        action: Action description
        user_id: User ID (safe to log)
        **extra: Additional context (will be sanitized)
    """
    logger.info(
        action,
        user_id=user_id,
        action_type="user_action",
        **extra
    )


def log_security_event(logger: SecureLogger, event: str, **extra):
    """
    Log security event with high priority
    
    Args:
        logger: SecureLogger instance
        event: Security event description
        **extra: Additional context (will be sanitized)
    """
    logger.warning(
        event,
        event_type="security",
        **extra
    )

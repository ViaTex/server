import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional, Union, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database import get_db

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()
# Optional bearer that does not auto-error when missing
security_optional = HTTPBearer(auto_error=False)


class SecurityManager:
    """Security manager for authentication and authorization"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """Generate a secure random password"""
        import string
        # Use a mix of uppercase, lowercase, digits, and special characters
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        # Ensure at least one character from each category
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special_chars)
        ]
        
        # Fill the rest with random characters from all categories
        all_chars = uppercase + lowercase + digits + special_chars
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))
        
        # Shuffle the password to make it more random
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        
        return ''.join(password_list)
    
    @staticmethod
    def create_access_token(
        subject: Union[str, Any], 
        expires_delta: Optional[timedelta] = None,
        user_type: str = "student",
        tenant_id: Optional[str] = None
    ) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "access",
            "user_type": user_type,
            "tenant_id": tenant_id,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4())
        }
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        logger.info(f"Created access token for user {subject} of type {user_type}")
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        subject: Union[str, Any],
        tenant_id: Optional[str] = None
    ) -> str:
        """Create JWT refresh token"""
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "refresh",
            "tenant_id": tenant_id,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4())
        }
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        logger.info(f"Created refresh token for user {subject}")
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def create_sso_token(
        user_id: str,
        email: str,
        name: str,
        user_type: str = "student",
        tenant_id: Optional[str] = None
    ) -> str:
        """Create SSO token for external services"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)  # Short-lived for SSO
        
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "name": name,
            "user_type": user_type,
            "tenant_id": tenant_id,
            "iat": datetime.now(timezone.utc),
            "exp": expire,
            "iss": "disha-platform"
        }
        
        secret = settings.RESUME_BUILDER_JWT_SECRET or settings.SECRET_KEY
        encoded_jwt = jwt.encode(
            to_encode,
            secret,
            algorithm=settings.ALGORITHM
        )
        
        logger.info(f"Created SSO token for user {user_id}")
        return encoded_jwt


# Dependency to get current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = SecurityManager.verify_token(token)
    
    user_id: str = payload.get("sub")
    user_type: str = payload.get("user_type", "student")
    tenant_id: str = payload.get("tenant_id")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user_id,
        "user_type": user_type,
        "tenant_id": tenant_id,
        "token_payload": payload
    }


# Dependency to get current student
async def get_current_student(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current student user"""
    if current_user["user_type"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student account required."
        )
    return current_user


# Dependency to get current corporate
async def get_current_corporate(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current corporate user"""
    if current_user["user_type"] != "corporate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Corporate account required."
        )
    return current_user


# Dependency to get current college
async def get_current_college(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current college user"""
    if current_user["user_type"] != "college":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. College account required."
        )
    return current_user


# Dependency to get current admin
async def get_current_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current admin user"""
    if current_user["user_type"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin account required."
        )
    return current_user


# Optional authentication dependency (non-failing when header missing)
async def check_student_access(
    current_student: dict = Depends(get_current_student),
    db: Session = Depends(get_db)
) -> dict:
    """Dependency to check if student has access based on license"""
    from uuid import UUID
    from app.services.student_access_service import StudentAccessService
    from app.models.user import Student, College
    
    access_service = StudentAccessService(db)
    access_check = access_service.check_student_access(UUID(current_student["user_id"]))
    
    if not access_check["has_access"]:
        # Get college info for error response
        student = db.query(Student).filter(Student.id == UUID(current_student["user_id"])).first()
        college_name = None
        college_email = None
        if student and student.college_id:
            college = db.query(College).filter(College.id == student.college_id).first()
            if college:
                college_name = college.college_name
                college_email = college.email
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": access_check["reason"],
                "college_name": college_name,
                "college_email": college_email
            }
        )
    
    return current_student


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = SecurityManager.verify_token(token)
        return {
            "user_id": payload.get("sub"),
            "user_type": payload.get("user_type", "student"),
            "tenant_id": payload.get("tenant_id"),
            "token_payload": payload,
        }
    except HTTPException:
        return None


# Rate limiting utilities
class RateLimiter:
    """Simple rate limiter using Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def is_allowed(self, key: str, limit: int = 60, window: int = 60) -> bool:
        """Check if request is allowed based on rate limit"""
        current = await self.redis.get(key)
        if current is None:
            await self.redis.setex(key, window, 1)
            return True
        
        count = int(current)
        if count >= limit:
            return False
        
        await self.redis.incr(key)
        return True


# Password validation
def validate_password(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 8:
        return False
    
    # Check for at least one uppercase, lowercase, digit, and special character
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    return has_upper and has_lower and has_digit and has_special


# Email validation
def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# Phone validation
def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    import re
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid Indian phone number (10 digits)
    if len(digits_only) == 10:
        return True
    
    # Check if it's a valid international number (10-15 digits)
    if 10 <= len(digits_only) <= 15:
        return True
    
    return False

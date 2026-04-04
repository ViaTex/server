from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional
import uuid
from datetime import datetime, timedelta, timezone
import structlog

from app.models.user import Student, Corporate, College, Admin, UserSession, UserStatus, SessionUserType
from app.models.user import EmailOTP
from app.core.security import SecurityManager
from app.schemas.auth import (
    StudentRegisterRequest,
    CorporateRegisterRequest,
    CollegeRegisterRequest
)
from app.core.config import settings

logger = structlog.get_logger()

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _get_db_user_type(self, user_type: str) -> str:
        normalized_user_type = (user_type or "").strip().lower()
        if normalized_user_type in {"college", "university"}:
            return SessionUserType.COLLEGE
        if normalized_user_type == "student":
            return SessionUserType.STUDENT
        if normalized_user_type == "corporate":
            return SessionUserType.CORPORATE
        if normalized_user_type == "admin":
            return SessionUserType.ADMIN
        raise ValueError("Invalid user type")

    def _is_email_taken(self, email: str) -> bool:
        if self.db.query(Student).filter(Student.email == email).first(): return True
        if self.db.query(Corporate).filter(Corporate.email == email).first(): return True
        if self.db.query(College).filter(College.email == email).first(): return True
        if self.db.query(Admin).filter(Admin.email == email).first(): return True
        return False

    def _find_user_by_email(self, email: str) -> Tuple[object, str]:
        """Find user by email across all user types and return (user, user_type)"""
        user = self.db.query(Student).filter(Student.email == email).first()
        if user:
            return user, "student"
        
        user = self.db.query(Corporate).filter(Corporate.email == email).first()
        if user:
            return user, "corporate"
        
        user = self.db.query(College).filter(College.email == email).first()
        if user:
            return user, "college"
        
        user = self.db.query(Admin).filter(Admin.email == email).first()
        if user:
            return user, "admin"
        
        return None, None

    def _generate_student_unique_id(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"ST{year}"
        last = (
            self.db.query(Student.student_unique_id)
            .filter(Student.student_unique_id.like(f"{prefix}%"))
            .order_by(Student.student_unique_id.desc())
            .first()
        )
        next_seq = 1
        if last and last[0]:
            try:
                next_seq = int(str(last[0])[-4:]) + 1
            except Exception:
                next_seq = 1
        return f"{prefix}{next_seq:04d}"

    async def send_signup_email_otp(self, email: str) -> None:
        if self._is_email_taken(email):
            raise ValueError("Email already registered")

        code = str(uuid.uuid4().int)[0:6]
        self.db.query(EmailOTP).filter(EmailOTP.email == email, EmailOTP.used == False).delete()
        otp = EmailOTP(
            email=email,
            code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        self.db.add(otp)
        self.db.commit()
        logger.info(f"Signup OTP generated for {email}: {code}")
        # MOCK SEND EMAIL: In a real app, integrate SMTP here.

    def _consume_email_otp(self, email: str, code: str) -> None:
        record = self.db.query(EmailOTP).filter(
            EmailOTP.email == email,
            EmailOTP.code == code,
            EmailOTP.used == False,
            EmailOTP.expires_at > datetime.now(timezone.utc),
        ).first()
        if not record:
            raise ValueError("Invalid or expired OTP")
        record.used = True
        self.db.commit()

    async def verify_otp_and_register_student(self, code: str, request: StudentRegisterRequest) -> Student:
        self._consume_email_otp(request.email, code)
        return await self.register_student(request)

    async def verify_otp_and_register_corporate(self, code: str, request: CorporateRegisterRequest) -> Corporate:
        self._consume_email_otp(request.email, code)
        return await self.register_corporate(request)

    async def verify_otp_and_register_college(self, code: str, request: CollegeRegisterRequest) -> College:
        self._consume_email_otp(request.email, code)
        return await self.register_college(request)

    async def register_student(self, request: StudentRegisterRequest) -> Student:
        try:
            if self._is_email_taken(request.email):
                raise ValueError("Email already registered")


            education_entries = []
            if request.institution:
                education_entries.append(
                    {
                        "id": str(uuid.uuid4()),
                        "level": "Other",
                        "custom_level": "Not specified",
                        "institution": request.institution,
                        "start_date": "",
                        "end_date": "",
                        "score": "",
                        "description": "",
                    }
                )

            student = Student(
                id=uuid.uuid4(),
                email=request.email,
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.name,
                phone=request.phone,
                education=education_entries,
                has_accepted_terms=True,
                student_unique_id=self._generate_student_unique_id(),
            )

            for _ in range(5):
                try:
                    self.db.add(student)
                    self.db.commit()
                    self.db.refresh(student)
                    return student
                except IntegrityError as e:
                    self.db.rollback()
                    if "student_unique_id" in str(e).lower():
                        student.student_unique_id = self._generate_student_unique_id()
                        continue
                    raise
        except Exception as e:
            self.db.rollback()
            logger.error("Student registration failed", error=str(e), email=request.email)
            raise

    async def register_corporate(self, request: CorporateRegisterRequest) -> Corporate:
        try:
            if self._is_email_taken(request.email):
                raise ValueError("Email already registered")

            corporate = Corporate(
                id=uuid.uuid4(),
                email=request.email,
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.contact_person or request.company_name,
                company_name=request.company_name,
                has_accepted_terms=True,
            )
            self.db.add(corporate)
            self.db.commit()
            self.db.refresh(corporate)
            return corporate
        except Exception as e:
            self.db.rollback()
            logger.error("Corporate registration failed", error=str(e), email=request.email)
            raise

    async def register_college(self, request: CollegeRegisterRequest) -> College:
        try:
            if self._is_email_taken(request.email):
                raise ValueError("Email already registered")

            college = College(
                id=uuid.uuid4(),
                email=request.email,
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.contact_person_name or request.college_name,
                college_name=request.college_name,
                status=UserStatus.INACTIVE
            )
            self.db.add(college)
            self.db.commit()
            self.db.refresh(college)
            return college
        except Exception as e:
            self.db.rollback()
            logger.error("College registration failed", error=str(e), email=request.email)
            raise

    async def login(self, email: str, password: str, user_type: Optional[str] = None) -> Tuple[object, str, str]:
        try:
            # If user_type is provided, use the old logic for backward compatibility
            if user_type:
                if user_type == "student":
                    user = self.db.query(Student).filter(Student.email == email).first()
                elif user_type == "corporate":
                    user = self.db.query(Corporate).filter(Corporate.email == email).first()
                elif user_type == "college":
                    user = self.db.query(College).filter(College.email == email).first()
                elif user_type == "admin":
                    user = self.db.query(Admin).filter(Admin.email == email).first()
                else:
                    raise ValueError("Invalid user type")

                if not user:
                    raise ValueError("User not found")
            else:
                # If user_type not provided, find user across all tables
                user, determined_user_type = self._find_user_by_email(email)
                if not user:
                    raise ValueError("User not found")
                user_type = determined_user_type

            if not SecurityManager.verify_password(password, user.password_hash):
                raise ValueError("Invalid password")

            user.last_login = datetime.now(timezone.utc)
            self.db.commit()

            access_token = SecurityManager.create_access_token(
                subject=str(user.id),
                user_type=user_type,
                tenant_id=getattr(user, 'tenant_id', "default")
            )
            refresh_token = SecurityManager.create_refresh_token(
                subject=str(user.id),
                tenant_id=getattr(user, 'tenant_id', "default")
            )

            session = UserSession(
                id=uuid.uuid4(),
                user_id=user.id,
                user_type=self._get_db_user_type(user_type),
                session_token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            self.db.add(session)
            self.db.commit()

            return user, access_token, refresh_token
        except Exception as e:
            self.db.rollback()
            logger.error("Login failed", error=str(e), email=email, user_type=user_type)
            raise

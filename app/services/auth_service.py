from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple
import uuid
from datetime import datetime, timedelta, timezone
import structlog

from app.models.user import Student, Corporate, College, Mentor, Admin, UserSession, UserStatus, UserType
from app.models.user import EmailOTP
from app.core.security import SecurityManager
from app.schemas.auth import (
    StudentRegisterRequest,
    CorporateRegisterRequest,
    CollegeRegisterRequest,
    MentorRegisterRequest,
)
from app.core.config import settings

logger = structlog.get_logger()

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _is_email_taken(self, email: str) -> bool:
        if self.db.query(Student).filter(Student.email == email).first(): return True
        if self.db.query(Corporate).filter(Corporate.email == email).first(): return True
        if self.db.query(College).filter(College.email == email).first(): return True
        if self.db.query(Mentor).filter(Mentor.email_id == email).first(): return True
        if self.db.query(Admin).filter(Admin.email == email).first(): return True
        return False

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

    def _generate_mentor_id(self) -> str:
        prefix = "MT2026"
        last = (
            self.db.query(Mentor.mentor_id)
            .filter(Mentor.mentor_id.like(f"{prefix}%"))
            .order_by(Mentor.mentor_id.desc())
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

    async def register_mentor(self, request: MentorRegisterRequest) -> Mentor:
        try:
            if self._is_email_taken(str(request.email_id)):
                raise ValueError("Email already registered")

            if request.total_experience < 5:
                raise ValueError("Mentor must have at least 5 years of experience")

            mentor = Mentor(
                id=uuid.uuid4(),
                mentor_id=self._generate_mentor_id(),
                full_name=request.full_name,
                email_id=str(request.email_id),
                phone_number=request.phone_number,
                password_hash=SecurityManager.get_password_hash(request.password),
                current_company=request.current_company,
                total_experience=request.total_experience,
                domain_expertise=request.domain_expertise or [],
            )

            for _ in range(5):
                try:
                    self.db.add(mentor)
                    self.db.commit()
                    self.db.refresh(mentor)
                    return mentor
                except IntegrityError as e:
                    self.db.rollback()
                    if "mentor_id" in str(e).lower():
                        mentor.mentor_id = self._generate_mentor_id()
                        continue
                    raise
        except Exception as e:
            self.db.rollback()
            logger.error("Mentor registration failed", error=str(e), email=str(request.email_id))
            raise

    def _is_mentor_locked(self, mentor: Mentor) -> bool:
        if not mentor.locked_until:
            return False
        now = datetime.now(timezone.utc)
        return mentor.locked_until > now

    def _increment_mentor_failed_attempt(self, mentor: Mentor) -> None:
        now = datetime.now(timezone.utc)
        mentor.failed_attempts = (mentor.failed_attempts or 0) + 1
        if mentor.failed_attempts >= 5:
            mentor.locked_until = now + timedelta(hours=2)
        self.db.commit()

    def _reset_mentor_login_security(self, mentor: Mentor) -> None:
        mentor.failed_attempts = 0
        mentor.locked_until = None

    async def register_student(self, request: StudentRegisterRequest) -> Student:
        try:
            if self._is_email_taken(request.email):
                raise ValueError("Email already registered")

            if not request.has_accepted_terms:
                raise ValueError("Terms and policies must be accepted")

            terms_version = request.accepted_terms_version or settings.TERMS_VERSION

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
                accepted_terms_version=terms_version,
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

            if not request.has_accepted_terms:
                raise ValueError("Terms and policies must be accepted")

            terms_version = request.accepted_terms_version or settings.TERMS_VERSION

            corporate = Corporate(
                id=uuid.uuid4(),
                email=request.email,
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.contact_person or request.company_name,
                company_name=request.company_name,
                has_accepted_terms=True,
                accepted_terms_version=terms_version,
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

    async def login(self, email: str, password: str, user_type: str) -> Tuple[object, str, str]:
        try:
            if user_type == "student":
                user = self.db.query(Student).filter(Student.email == email).first()
            elif user_type == "corporate":
                user = self.db.query(Corporate).filter(Corporate.email == email).first()
            elif user_type == "college":
                user = self.db.query(College).filter(College.email == email).first()
            elif user_type == "mentor":
                user = self.db.query(Mentor).filter(Mentor.email_id == email).first()
            elif user_type == "admin":
                user = self.db.query(Admin).filter(Admin.email == email).first()
            else:
                raise ValueError("Invalid user type")

            if not user:
                raise ValueError("User not found")

            if user_type == "mentor":
                if user.locked_until and user.locked_until <= datetime.now(timezone.utc):
                    self._reset_mentor_login_security(user)
                    self.db.commit()
                elif self._is_mentor_locked(user):
                    raise ValueError("Account locked due to multiple failed attempts. Please try again after 2 hours")

            if not SecurityManager.verify_password(password, user.password_hash):
                if user_type == "mentor":
                    self._increment_mentor_failed_attempt(user)
                raise ValueError("Invalid password")

            if user_type == "mentor":
                self._reset_mentor_login_security(user)
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
                user_type=UserType[user_type.upper()],
                session_token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            self.db.add(session)
            self.db.commit()

            return user, access_token, refresh_token
        except Exception as e:
            logger.error("Login failed", error=str(e), email=email, user_type=user_type)
            raise

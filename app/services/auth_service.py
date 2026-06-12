# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional
import uuid
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
# pyrefly: ignore [missing-import]
import structlog

from app.models.user import (
    Student,
    Mentor,
    Corporate,
    College,
    Admin,
    UserSession,
    UserStatus,
    SessionUserType,
    EmailOTP,
    PasswordResetOTP,
    PasswordResetToken,
    EmailVerificationToken,
    PasswordHistory,
    AuthAuditLog,
)
from app.core.security import SecurityManager, validate_phone
from app.core.mail import send_email, MailAuthError, MailConfigError, MailSendError
from app.schemas.auth import (
    StudentRegisterRequest,
    MentorRegisterRequest,
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
        if normalized_user_type == "mentor":
            return SessionUserType.MENTOR
        if normalized_user_type == "corporate":
            return SessionUserType.CORPORATE
        if normalized_user_type == "admin":
            return SessionUserType.ADMIN
        raise ValueError("Invalid user type")

    def _is_email_taken(self, email: str) -> bool:
        if self.db.query(Student).filter(Student.email == email).first(): return True
        if self.db.query(Mentor).filter(Mentor.email == email).first(): return True
        if self.db.query(Corporate).filter(Corporate.email == email).first(): return True
        if self.db.query(College).filter(College.email == email).first(): return True
        if self.db.query(Admin).filter(Admin.email == email).first(): return True
        return False

    def _find_user_by_email(self, email: str) -> Tuple[object, str]:
        """Find user by email across all user types and return (user, user_type)"""
        user = self.db.query(Student).filter(Student.email == email).first()
        if user:
            return user, "student"

        user = self.db.query(Mentor).filter(Mentor.email == email).first()
        if user:
            return user, "mentor"
        
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
        try:
            self._send_email(
                email,
                "DishaSetu Signup Verification OTP",
                f"Your signup OTP is: {code}\nThis OTP expires in 10 minutes.",
                html_body=self._otp_email_html(
                    title="Verify Your Email",
                    otp_code=code,
                    helper_text="Use this one-time password to verify your DishaSetu account.",
                    expires_minutes=10
                )
            )
        except Exception as email_error:
            logger.error("Failed to send signup OTP email", error=str(email_error), email=email)
            raise ValueError("Unable to send verification email right now. Please try again.")

    def _send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None, background: bool = True) -> None:
        def do_send():
            try:
                send_email(to_email=to_email, subject=subject, body=body, html_body=html_body)
            except Exception as exc:
                logger.error("Failed to send email via SMTP", error=str(exc), to=to_email, subject=subject)
                if settings.MAIL_DEV_FALLBACK or settings.APP_ENV == "development" or settings.DEBUG:
                    logger.warning(
                        "SMTP delivery failed, but bypassed due to development/debug mode. Printed email details below:",
                        to=to_email,
                        subject=subject,
                        body=body
                    )
                    return
                # Background thread exceptions are logged but won't crash main request.
                if isinstance(exc, MailConfigError):
                    raise ValueError("Email service is not configured on the server") from exc
                if isinstance(exc, MailAuthError):
                    raise ValueError(
                        "SMTP authentication failed. For Gmail use an App Password (not your normal Gmail password)."
                    ) from exc
                raise ValueError(f"Email delivery failed: {str(exc)}") from exc

        if background:
            import threading
            threading.Thread(target=do_send, daemon=True).start()
        else:
            do_send()

    def _otp_email_html(
        self,
        *,
        title: str,
        otp_code: str,
        helper_text: str,
        expires_minutes: int,
        cta_link: Optional[str] = None
    ) -> str:
        cta_html = ""
        if cta_link:
            cta_html = (
                f'<p style="margin:20px 0;">'
                f'<a href="{cta_link}" style="background:#2b6ef2;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:600;display:inline-block;">Continue Securely</a>'
                f"</p>"
            )
        return f"""
<html>
  <body style="font-family:Arial,sans-serif;background:#f6f8fc;padding:24px;">
    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e6ebf5;border-radius:12px;padding:24px;">
      <h2 style="margin:0 0 8px 0;color:#1c2b4a;">{title}</h2>
      <p style="color:#3f4f6b;line-height:1.5;">{helper_text}</p>
      <div style="margin:20px 0;padding:16px;border:1px dashed #9db2da;border-radius:10px;background:#f1f6ff;text-align:center;">
        <div style="font-size:28px;letter-spacing:8px;font-weight:700;color:#163b82;">{otp_code}</div>
        <div style="margin-top:6px;font-size:12px;color:#5b6f93;">Expires in {expires_minutes} minutes</div>
      </div>
      {cta_html}
      <p style="font-size:12px;color:#6d7f9f;">If you did not request this, please ignore this email.</p>
    </div>
  </body>
</html>
"""

    async def send_mail_test(self, email: str) -> None:
        self._send_email(
            email,
            "DishaSetu SMTP Test",
            "This is a test email from DishaSetu. If you received this, SMTP is configured correctly.",
            background=False
        )

    async def send_password_reset_otp(self, email: str) -> None:
        user, _ = self._find_user_by_email(email)
        if not user:
            raise ValueError("No account found with this email")

        code = self._generate_numeric_otp()
        self.db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email,
            PasswordResetOTP.used == False
        ).delete()
        otp = PasswordResetOTP(
            email=email,
            code=code,
            expires_at=self._now() + timedelta(minutes=10),
        )
        self.db.add(otp)
        self.db.commit()

        subject = "DishaSetu Password Reset OTP"
        body = (
            "We received a request to reset your DishaSetu password.\n\n"
            f"Your OTP is: {code}\n"
            "This OTP expires in 10 minutes.\n\n"
            "If you did not request this, you can ignore this email."
        )

        try:
            self._send_email(
                email,
                subject,
                body,
                html_body=self._otp_email_html(
                    title="Password Reset OTP",
                    otp_code=code,
                    helper_text="Use this OTP to continue resetting your password.",
                    expires_minutes=10
                )
            )
        except Exception as email_error:
            logger.error("Failed to send password reset email", error=str(email_error), email=email)
            raise ValueError("Unable to send reset email right now. Please try again.")

    async def reset_password_with_otp(self, email: str, code: str, new_password: str) -> None:
        otp = self.db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email,
            PasswordResetOTP.code == code,
            PasswordResetOTP.used == False,
            PasswordResetOTP.expires_at > datetime.now(timezone.utc),
        ).first()
        if not otp:
            raise ValueError("Invalid or expired OTP")

        user, _ = self._find_user_by_email(email)
        if not user:
            raise ValueError("No account found with this email")

        user.password_hash = SecurityManager.get_password_hash(new_password)
        otp.used = True
        self.db.commit()

    def _consume_email_otp(self, email: str, code: str) -> None:
        record = self.db.query(EmailOTP).filter(
            EmailOTP.email == email,
            EmailOTP.code == code,
            EmailOTP.used == False,
            EmailOTP.expires_at > self._now(),
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

    async def verify_otp_and_register_mentor(self, code: str, request: MentorRegisterRequest) -> Mentor:
        self._consume_email_otp(request.email, code)
        return await self.register_mentor(request)

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
                email=request.email.lower(),
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.name,
                phone=request.phone,
                education=education_entries,
                has_accepted_terms=True,
                student_unique_id=self._generate_student_unique_id(),
                email_verified=True,
            )

            for _ in range(5):
                try:
                    self.db.add(student)
                    self.db.commit()
                    self.db.refresh(student)
                    self._record_password_history(student.email, student.password_hash)
                    await self.create_email_verification(student.email)
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
                email=request.email.lower(),
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.contact_person or request.company_name,
                company_name=request.company_name,
                has_accepted_terms=True,
                email_verified=True,
            )
            self.db.add(corporate)
            self.db.commit()
            self.db.refresh(corporate)
            self._record_password_history(corporate.email, corporate.password_hash)
            await self.create_email_verification(corporate.email)
            return corporate
        except Exception as e:
            self.db.rollback()
            logger.error("Corporate registration failed", error=str(e), email=request.email)
            raise

    async def register_mentor(self, request: MentorRegisterRequest) -> Mentor:
        try:
            if self._is_email_taken(request.email):
                raise ValueError("Email already registered")

            mentor = Mentor(
                id=uuid.uuid4(),
                user_id=uuid.UUID(str(request.user_id)) if request.user_id else uuid.uuid4(),
                email=request.email.lower(),
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.name,
                phone=request.phone,
                current_role=request.current_role,
                expertise_areas=request.expertise_areas or [],
                experience_years=request.experience_years,
                motivation=request.motivation,
                email_verified=True,
            )
            self.db.add(mentor)
            self.db.commit()
            self.db.refresh(mentor)
            self._record_password_history(mentor.email, mentor.password_hash)
            await self.create_email_verification(mentor.email)
            return mentor
        except Exception as e:
            self.db.rollback()
            logger.error("Mentor registration failed", error=str(e), email=request.email)
            raise

    async def register_college(self, request: CollegeRegisterRequest) -> College:
        try:
            if self._is_email_taken(request.email):
                raise ValueError("Email already registered")

            college = College(
                id=uuid.uuid4(),
                email=request.email.lower(),
                password_hash=SecurityManager.get_password_hash(request.password),
                name=request.contact_person_name or request.college_name,
                college_name=request.college_name,
                status=UserStatus.INACTIVE,
                email_verified=True,
            )
            self.db.add(college)
            self.db.commit()
            self.db.refresh(college)
            self._record_password_history(college.email, college.password_hash)
            await self.create_email_verification(college.email)
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
                elif user_type == "mentor":
                    user = self.db.query(Mentor).filter(Mentor.email == email).first()
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

            # Ensure the account is verified before checking the password (auto-verify if not verified)
            if not user.email_verified:
                user.email_verified = True
                self.db.commit()
            if not SecurityManager.verify_password(password, user.password_hash):
                raise ValueError("Invalid password")

            user.last_login = self._now()
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
                expires_at=self._now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            self.db.add(session)
            self.db.commit()

            return user, access_token, refresh_token
        except Exception as e:
            self.db.rollback()
            logger.error("Login failed", error=str(e), email=email, user_type=user_type)
            raise

    async def create_email_verification(self, email: str) -> None:
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        otp = self._generate_numeric_otp()
        self.db.query(EmailVerificationToken).filter(
            EmailVerificationToken.email == email,
            EmailVerificationToken.used == False
        ).delete()
        self.db.add(
            EmailVerificationToken(
                email=email,
                token_hash=token_hash,
                otp_code=otp,
                expires_at=self._now() + timedelta(minutes=30),
            )
        )
        self.db.commit()
        verify_link = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        try:
            self._send_email(
                email,
                "Verify your DishaSetu account",
                f"Verify your email using this link:\n{verify_link}\n\nOr use OTP: {otp}\nExpires in 30 minutes.",
                html_body=self._otp_email_html(
                    title="Account Verification",
                    otp_code=otp,
                    helper_text="Verify your email using the OTP below or continue with the secure link.",
                    expires_minutes=30,
                    cta_link=verify_link
                )
            )
        except Exception as email_error:
            logger.error("Failed to send email verification", error=str(email_error), email=email)
            if settings.MAIL_DEV_FALLBACK or settings.APP_ENV == "development" or settings.DEBUG:
                logger.warning(
                    "Email verification bypassed / printed to logs due to MAIL_DEV_FALLBACK/development mode.",
                    verify_link=verify_link,
                    otp=otp
                )
                user, _ = self._find_user_by_email(email)
                if user:
                    user.email_verified = True
                    self.db.commit()
                return
            raise ValueError("Unable to send verification email right now. Please try again.")

    async def verify_email_by_token(self, token: str) -> None:
        token_hash = self._hash_token(token)
        record = self.db.query(EmailVerificationToken).filter(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used == False
        ).first()
        if not record or record.expires_at <= self._now():
            raise ValueError("Invalid or expired verification link")
        user, _ = self._find_user_by_email(record.email)
        if not user:
            raise ValueError("Invalid verification request")
        user.email_verified = True
        record.used = True
        self.db.commit()

    async def verify_email_by_otp(self, email: str, otp: str) -> None:
        record = self.db.query(EmailVerificationToken).filter(
            EmailVerificationToken.email == email.lower(),
            EmailVerificationToken.used == False
        ).order_by(EmailVerificationToken.created_at.desc()).first()
        if not record:
            raise ValueError("Invalid verification request")
        if record.expires_at <= self._now():
            raise ValueError("Verification OTP expired")
        if record.attempt_count >= record.max_attempts:
            raise ValueError("Too many invalid OTP attempts")
        if record.otp_code != otp:
            record.attempt_count += 1
            self.db.commit()
            raise ValueError("Invalid OTP")
        user, _ = self._find_user_by_email(email.lower())
        if not user:
            raise ValueError("Invalid verification request")
        user.email_verified = True
        record.used = True
        self.db.commit()

    async def start_forgot_password(
        self,
        identifier: str,
        *,
        channel: str = "email",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        user, _ = self._find_user_by_identifier(identifier)
        # Never expose account existence
        generic = {"message": "If an account exists, recovery instructions were sent."}
        if not user:
            self._log_audit(email=None, action="forgot_password_start", status="masked_not_found", ip_address=ip_address, user_agent=user_agent)
            return generic

        email = user.email.lower()
        otp_code = self._generate_numeric_otp()
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        self.db.query(PasswordResetOTP).filter(PasswordResetOTP.email == email, PasswordResetOTP.used == False).delete()
        self.db.query(PasswordResetToken).filter(PasswordResetToken.email == email, PasswordResetToken.used == False).delete()
        self.db.add(PasswordResetOTP(
            email=email,
            code=otp_code,
            expires_at=self._now() + timedelta(minutes=10),
            max_attempts=5,
            next_resend_at=self._now() + timedelta(seconds=60),
        ))
        self.db.add(PasswordResetToken(
            email=email,
            token_hash=token_hash,
            expires_at=self._now() + timedelta(minutes=20),
        ))
        self.db.commit()

        reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={raw_token}"
        try:
            if channel == "sms" and user.phone and validate_phone(user.phone):
                logger.info("SMS OTP (mock)", phone=user.phone, otp=otp_code)
            else:
                self._send_email(
                    email,
                    "DishaSetu Password Recovery OTP",
                    f"OTP: {otp_code}\nReset link: {reset_link}\nOTP expires in 10 min. Link expires in 20 min.",
                    html_body=self._otp_email_html(
                        title="Password Recovery OTP",
                        otp_code=otp_code,
                        helper_text="Use this OTP and secure link to reset your password.",
                        expires_minutes=10,
                        cta_link=reset_link
                    )
                )
        except Exception as email_error:
            logger.error("Failed to send password recovery email", error=str(email_error), email=email)
            self._log_audit(
                email=email,
                action="forgot_password_start",
                status="mail_failed",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"error": str(email_error)}
            )
            # Developer-friendly fallback for local testing when explicitly enabled.
            if settings.MAIL_DEV_FALLBACK:
                return {
                    **generic,
                    "warning": "Email delivery failed; using development fallback payload.",
                    "debug_reset_link": reset_link,
                    "debug_otp": otp_code,
                }
            raise ValueError("Unable to send recovery email right now. Please try again.")
        self._log_audit(email=email, action="forgot_password_start", status="success", ip_address=ip_address, user_agent=user_agent)
        return generic

    async def resend_forgot_password_otp(self, identifier: str, channel: str = "email") -> dict:
        user, _ = self._find_user_by_identifier(identifier)
        generic = {"message": "If an account exists, OTP has been resent."}
        if not user:
            return generic
        email = user.email.lower()
        otp = self.db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email,
            PasswordResetOTP.used == False
        ).order_by(PasswordResetOTP.created_at.desc()).first()
        if not otp:
            return generic
        if otp.next_resend_at and otp.next_resend_at > self._now():
            remaining = int((otp.next_resend_at - self._now()).total_seconds())
            if remaining < 1:
                remaining = 1
            raise ValueError(f"OTP_RESEND_COOLDOWN:{remaining}")
        otp.code = self._generate_numeric_otp()
        otp.expires_at = self._now() + timedelta(minutes=10)
        otp.resend_count += 1
        otp.next_resend_at = self._now() + timedelta(seconds=60)
        self.db.commit()
        if channel == "sms" and user.phone and validate_phone(user.phone):
            logger.info("Resend SMS OTP (mock)", phone=user.phone, otp=otp.code)
        else:
            try:
                self._send_email(
                    email,
                    "DishaSetu Password Recovery OTP",
                    f"Your OTP is {otp.code}. Expires in 10 minutes.",
                    html_body=self._otp_email_html(
                        title="Resent Password Recovery OTP",
                        otp_code=otp.code,
                        helper_text="Use this refreshed OTP to continue password recovery.",
                        expires_minutes=10
                    )
                )
            except Exception as email_error:
                logger.error("Failed to resend password recovery OTP", error=str(email_error), email=email)
                raise ValueError(f"OTP_RESEND_EMAIL_FAILED:{str(email_error)}")
        return {
            **generic,
            "cooldown_seconds": 60
        }

    async def verify_forgot_password_otp(self, identifier: str, otp: str) -> dict:
        user, _ = self._find_user_by_identifier(identifier)
        if not user:
            raise ValueError("Invalid or expired OTP")
        email = user.email.lower()
        record = self.db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email,
            PasswordResetOTP.used == False
        ).order_by(PasswordResetOTP.created_at.desc()).first()
        if not record or record.expires_at <= self._now():
            raise ValueError("Invalid or expired OTP")
        if record.attempt_count >= record.max_attempts:
            raise ValueError("OTP attempts exceeded")
        if record.code != otp:
            record.attempt_count += 1
            self.db.commit()
            raise ValueError("Invalid or expired OTP")
        record.used = True
        self.db.commit()
        token = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.email == email,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > self._now()
        ).order_by(PasswordResetToken.created_at.desc()).first()
        if not token:
            raise ValueError("Reset session expired")
        return {"reset_token": token.token_hash}

    async def complete_forgot_password(self, reset_token: str, new_password: str) -> None:
        if not self._is_strong_password(new_password):
            raise ValueError("Password must include upper, lower, number, special and be at least 8 characters")
        token_hash = reset_token if len(reset_token) == 64 else self._hash_token(reset_token)
        token = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > self._now()
        ).first()
        if not token:
            raise ValueError("Invalid or expired reset token")
        user, _ = self._find_user_by_email(token.email)
        if not user:
            raise ValueError("Invalid reset request")
        self._ensure_new_password_not_reused(user.email, new_password)
        user.password_hash = SecurityManager.get_password_hash(new_password)
        token.used = True
        self._record_password_history(user.email, user.password_hash)
        self.db.commit()
        self._revoke_all_sessions(user.id, reason="password_reset")
        try:
            self._send_email(user.email, "Password changed", "Your password was changed. If this wasn't you, contact support immediately.")
        except Exception as email_error:
            logger.warning("Failed to send password-changed alert", error=str(email_error), email=user.email)
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _hash_token(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _generate_numeric_otp(self, length: int = 6) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(length))

    def _is_strong_password(self, password: str) -> bool:
        return bool(
            len(password) >= 8
            and re.search(r"[A-Z]", password)
            and re.search(r"[a-z]", password)
            and re.search(r"\d", password)
            and re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password)
        )

    def _normalize_identifier(self, identifier: str) -> str:
        return (identifier or "").strip().lower()

    def _find_user_by_identifier(self, identifier: str) -> Tuple[object, str]:
        # Current system supports email across user tables; phone fallback keeps UX consistent.
        normalized = self._normalize_identifier(identifier)
        user, user_type = self._find_user_by_email(normalized)
        if user:
            return user, user_type
        # Phone lookup fallback
        for model, model_type in [
            (Student, "student"),
            (Mentor, "mentor"),
            (Corporate, "corporate"),
            (College, "college"),
            (Admin, "admin"),
        ]:
            candidate = self.db.query(model).filter(model.phone == identifier).first()
            if candidate:
                return candidate, model_type
        return None, None

    def _log_audit(
        self,
        *,
        email: Optional[str],
        action: str,
        status: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        self.db.add(
            AuthAuditLog(
                email=email,
                action=action,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
            )
        )
        self.db.commit()

    def _record_password_history(self, email: str, password_hash: str) -> None:
        self.db.add(PasswordHistory(email=email, password_hash=password_hash))
        self.db.commit()

    def _ensure_new_password_not_reused(self, email: str, new_password: str) -> None:
        last_hashes = (
            self.db.query(PasswordHistory)
            .filter(PasswordHistory.email == email)
            .order_by(PasswordHistory.created_at.desc())
            .limit(5)
            .all()
        )
        for entry in last_hashes:
            if SecurityManager.verify_password(new_password, entry.password_hash):
                raise ValueError("You cannot reuse your recent passwords")

    def _revoke_all_sessions(self, user_id: uuid.UUID, reason: str = "password_reset") -> None:
        sessions = self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None)
        ).all()
        for session in sessions:
            session.revoked_at = self._now()
            session.revoked_reason = reason
        self.db.commit()

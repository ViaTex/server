from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import (
    StudentRegisterRequest,
    MentorRegisterRequest,
    CorporateRegisterRequest,
    CollegeRegisterRequest,
    LoginRequest,
    OTPVerifyRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordStartRequest,
    ForgotPasswordOtpVerifyRequest,
    ForgotPasswordCompleteRequest,
    ResendOtpRequest,
    EmailVerificationLinkRequest,
    EmailVerificationOtpRequest,
    ResendEmailVerificationRequest,
    MailTestRequest,
)
from app.services.auth_service import AuthService
from pydantic import EmailStr

router = APIRouter()

@router.post("/send-otp")
async def send_otp(email: EmailStr, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.send_signup_email_otp(email)
        return {"message": "OTP sent successfully", "status": "success"}
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "invalid password" in msg.lower() or "incorrect password" in msg.lower():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
        if "verify your email" in msg.lower() or "email not verified" in msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during login")

@router.post("/register/student")
async def register_student(request: StudentRegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_student(request)
        return {
            "message": "Student registered successfully",
            "data": {"id": str(user.id), "email": user.email},
            "status": "success"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/register/corporate")
async def register_corporate(request: CorporateRegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_corporate(request)
        return {
            "message": "Corporate registered successfully",
            "data": {"id": str(user.id), "email": user.email},
            "status": "success"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register/mentor")
async def register_mentor(request: MentorRegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_mentor(request)
        return {
            "message": "Mentor registered successfully",
            "data": {"id": str(user.id), "email": user.email},
            "status": "success"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/register/college")
async def register_college(request: CollegeRegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_college(request)
        return {
            "message": "College registered successfully",
            "data": {"id": str(user.id), "email": user.email},
            "status": "success"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user, access_token, refresh_token = await auth_service.login(
            request.email, request.password, request.user_type
        )
        resolved_user_type = request.user_type or user.__class__.__name__.lower()
        return {
            "message": "Login successful",
            "status": "success",
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "user_type": resolved_user_type
                }
            }
        }
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "invalid password" in msg.lower() or "incorrect password" in msg.lower():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
        if "verify your email" in msg.lower() or "email not verified" in msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during login")

@router.post("/logout")
async def logout():
    # In a JWT stateless auth system, true logout happens client-side by destroying the tokens.
    # Currently, we just return a success message so the client can resolve the logout sequence safely.
    return {
        "message": "Logged out successfully",
        "status": "success"
    }


@router.post("/forgot-password/send-otp")
async def forgot_password_send_otp(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.send_password_reset_otp(request.email)
        return {"message": "Password reset OTP sent to your email", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send reset OTP")


@router.post("/forgot-password/reset")
async def forgot_password_reset(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.reset_password_with_otp(
            email=request.email,
            code=request.code,
            new_password=request.new_password
        )
        return {"message": "Password reset successful", "status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset password")


@router.post("/recovery/forgot-password/start")
async def forgot_password_start(request: ForgotPasswordStartRequest, req: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        payload = await auth_service.start_forgot_password(
            request.identifier,
            channel=request.channel,
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent"),
        )
        return {"status": "success", **payload}
    except ValueError as e:
        # Keep account-recovery response generic and successful to avoid user enumeration
        return {
            "status": "success",
            "message": "If an account exists, recovery instructions were sent.",
            "warning": str(e),
        }


@router.post("/recovery/forgot-password/resend-otp")
async def forgot_password_resend_otp(request: ResendOtpRequest, response: Response, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        payload = await auth_service.resend_forgot_password_otp(request.identifier, channel=request.channel)
        return {"status": "success", **payload}
    except ValueError as e:
        message = str(e)
        if message.startswith("OTP_RESEND_COOLDOWN:"):
            remaining = message.split(":", 1)[1]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"Please wait {remaining}s before requesting OTP again.",
                    "retry_after_seconds": int(remaining)
                },
                headers={"Retry-After": remaining}
            )
        if message.startswith("OTP_RESEND_EMAIL_FAILED:"):
            root = message.split(":", 1)[1]
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to resend OTP email right now. {root}"
            )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))


@router.post("/recovery/forgot-password/verify-otp")
async def forgot_password_verify_otp(payload: dict = Body(...), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        identifier = (
            str(payload.get("identifier") or payload.get("email") or payload.get("phone") or "").strip()
        )
        otp = str(payload.get("otp") or payload.get("code") or "").strip()
        if not identifier or not otp:
            raise ValueError("identifier/email/phone and otp/code are required")
        result = await auth_service.verify_forgot_password_otp(identifier, otp)
        return {"status": "success", "message": "OTP verified", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/recovery/forgot-password/complete")
async def forgot_password_complete(request: ForgotPasswordCompleteRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.complete_forgot_password(request.reset_token, request.new_password)
        return {"status": "success", "message": "Password has been reset"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verification/email/by-link")
async def verify_email_by_link(request: EmailVerificationLinkRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.verify_email_by_token(request.token)
        return {"status": "success", "message": "Email verified"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verification/email/by-otp")
async def verify_email_by_otp(request: EmailVerificationOtpRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.verify_email_by_otp(request.email, request.otp)
        return {"status": "success", "message": "Email verified"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verification/email/resend")
async def resend_email_verification(request: ResendEmailVerificationRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.create_email_verification(request.email.lower())
        return {"status": "success", "message": "Verification email sent if account exists"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/mail-test")
async def mail_test(request: MailTestRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.send_mail_test(request.email)
        return {"status": "success", "message": "SMTP test email sent"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"SMTP test failed: {str(e)}")

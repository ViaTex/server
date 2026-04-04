from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import (
    StudentRegisterRequest,
    CorporateRegisterRequest,
    CollegeRegisterRequest,
    LoginRequest,
    OTPVerifyRequest
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during login")

@router.post("/logout")
async def logout():
    # In a JWT stateless auth system, true logout happens client-side by destroying the tokens.
    # Currently, we just return a success message so the client can resolve the logout sequence safely.
    return {
        "message": "Logged out successfully",
        "status": "success"
    }

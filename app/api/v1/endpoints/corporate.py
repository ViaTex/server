from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_corporate
from app.models.user import Corporate
from app.schemas.corporate import CorporateProfileResponse, CorporateProfileUpdate

router = APIRouter()


@router.get("/profile", response_model=CorporateProfileResponse)
async def get_corporate_profile(
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate = db.query(Corporate).filter(Corporate.id == UUID(str(current_user["user_id"]))).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")
    return CorporateProfileResponse(
        id=str(corporate.id),
        email=corporate.email,
        name=corporate.name,
        bio=corporate.description,
        company_name=corporate.company_name,
        phone=corporate.phone,
        contact_person=corporate.contact_person,
        contact_designation=corporate.contact_designation,
        website_url=corporate.website_url,
        industry=corporate.industry,
        company_size=corporate.company_size,
        founded_year=corporate.founded_year,
        company_type=corporate.company_type,
        description=corporate.description,
        address=corporate.address,
    )


@router.patch("/profile", response_model=CorporateProfileResponse)
async def update_corporate_profile(
    payload: CorporateProfileUpdate,
    current_user: dict = Depends(get_current_corporate),
    db: Session = Depends(get_db),
):
    corporate = db.query(Corporate).filter(Corporate.id == UUID(str(current_user["user_id"]))).first()
    if not corporate:
        raise HTTPException(status_code=404, detail="Corporate profile not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "bio":
            corporate.description = value
        else:
            setattr(corporate, key, value)

    db.commit()
    db.refresh(corporate)
    return CorporateProfileResponse(
        id=str(corporate.id),
        email=corporate.email,
        name=corporate.name,
        bio=corporate.description,
        company_name=corporate.company_name,
        phone=corporate.phone,
        contact_person=corporate.contact_person,
        contact_designation=corporate.contact_designation,
        website_url=corporate.website_url,
        industry=corporate.industry,
        company_size=corporate.company_size,
        founded_year=corporate.founded_year,
        company_type=corporate.company_type,
        description=corporate.description,
        address=corporate.address,
    )

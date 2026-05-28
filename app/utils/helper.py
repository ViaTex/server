from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import HTTPException

from app.models.user import Gender, UserStatus


def normalize_empty(value: Any, required: bool, field: str) -> Any:
    if isinstance(value, str) and value.strip() == "":
        if required:
            raise HTTPException(status_code=400, detail=f"{field} cannot be empty")
        return None
    return value


def parse_status(value: Any, default: Optional[UserStatus] = UserStatus.ACTIVE) -> Optional[UserStatus]:
    if value in (None, ""):
        return default
    try:
        return UserStatus(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join([s.value for s in UserStatus])}",
        )


def parse_gender(value: Any) -> Optional[Gender]:
    if value in (None, ""):
        return None
    try:
        return Gender(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid gender. Must be one of: {', '.join([g.value for g in Gender])}",
        )


def parse_date(value: Any, field: str) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid {field} format. Use YYYY-MM-DD")
    return value


def parse_float(value: Any, field: str) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field} value")


def parse_int(value: Any, field: str) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field} value")


def normalize_expertise_areas(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return value
    raise HTTPException(status_code=400, detail="Invalid expertise_areas value")

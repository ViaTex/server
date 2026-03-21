from __future__ import annotations

import cloudinary
import cloudinary.uploader

from app.core.config import settings


class CloudinaryService:
    _configured = False

    @classmethod
    def _ensure_configured(cls) -> None:
        if cls._configured:
            return

        if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
            raise RuntimeError("Cloudinary credentials are not configured")

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        cls._configured = True

    @classmethod
    def upload_media_bytes(
        cls,
        media_bytes: bytes,
        *,
        folder: str,
        filename: str | None = None,
        resource_type: str = "auto",
    ) -> str:
        cls._ensure_configured()

        if not media_bytes:
            raise ValueError("Empty media content")

        upload_result = cloudinary.uploader.upload(
            media_bytes,
            folder=folder,
            resource_type=resource_type,
            use_filename=bool(filename),
            unique_filename=True,
            filename_override=filename,
        )
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise RuntimeError("Cloudinary upload did not return secure_url")
        return secure_url

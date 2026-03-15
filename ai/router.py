from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from ai.schemas import ResumeParsedResponse
from ai.services.resume_parser import ResumeParserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/parse-resume",
    response_model=ResumeParsedResponse,
    status_code=status.HTTP_200_OK,
)
async def parse_resume(resume: UploadFile = File(...)) -> ResumeParsedResponse:
    """Upload a PDF resume and return structured fields extracted via Groq+LangChain."""

    if resume is None:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = (resume.filename or "").lower()
    content_type = (resume.content_type or "").lower()
    if not (filename.endswith(".pdf") or content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported")

    try:
        content = await resume.read()
        service = ResumeParserService()
        return await service.parse_resume_pdf_bytes(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Resume parsing failed")
        raise HTTPException(status_code=500, detail=str(e))

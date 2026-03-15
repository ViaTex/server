from __future__ import annotations

from ai.schemas import ResumeParsedResponse
from ai.services.resume_parser import ResumeParserService


async def parse_resume_pdf_bytes(pdf_bytes: bytes) -> ResumeParsedResponse:
    """Convenience wrapper required by feature spec.

    Reuses the existing Groq/LangChain-based ResumeParserService.
    """

    service = ResumeParserService()
    return await service.parse_resume_pdf_bytes(pdf_bytes)

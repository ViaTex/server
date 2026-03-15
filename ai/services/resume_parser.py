from __future__ import annotations

import logging

import anyio
import orjson
from fastapi import HTTPException
from pydantic import ValidationError

from ai.chains.resume_chain import get_resume_extraction_chain
from ai.config import get_ai_settings
from ai.schemas import ResumeParsedResponse
from ai.services.bio_generator import BioGeneratorService
from ai.utils.pdf_loader import extract_text_from_pdf_bytes
from ai.utils.text_cleaner import clean_resume_text

logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> str:
    """Best-effort extraction of a JSON object from an LLM response."""
    if not text:
        return "{}"
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return text[start : end + 1]


class ResumeParserService:
    def __init__(self) -> None:
        self._bio_service = BioGeneratorService()

    async def parse_resume_pdf_bytes(self, pdf_bytes: bytes) -> ResumeParsedResponse:
        settings = get_ai_settings()
        if not settings.GROQ_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY is not configured in environment/.env",
            )

        raw_text = extract_text_from_pdf_bytes(pdf_bytes)
        cleaned_text = clean_resume_text(raw_text)
        if len(cleaned_text) > settings.MAX_RESUME_CHARS:
            logger.warning(
                "Resume text too long; truncating (max=%s, actual=%s)",
                settings.MAX_RESUME_CHARS,
                len(cleaned_text),
            )
            cleaned_text = cleaned_text[: settings.MAX_RESUME_CHARS]

        chain = get_resume_extraction_chain()

        try:
            # Threadpool because LangChain Groq client is sync.
            parsed: ResumeParsedResponse = await anyio.to_thread.run_sync(
                lambda: chain.invoke({"resume_text": cleaned_text})
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
        except Exception as e:
            # Fallback: accept raw string output and parse ourselves
            logger.warning(
                "Primary chain parsing failed; attempting fallback: %s",
                str(e),
            )
            try:
                raw = await anyio.to_thread.run_sync(
                    lambda: chain.invoke({"resume_text": cleaned_text, "force_text": True})
                )
                if isinstance(raw, ResumeParsedResponse):
                    parsed = raw
                else:
                    json_str = _extract_json_object(str(raw))
                    data = orjson.loads(json_str)
                    parsed = ResumeParsedResponse.model_validate(data)
            except Exception as inner:
                raise HTTPException(status_code=500, detail=f"LLM parsing failed: {inner}")

        bio = await self._bio_service.generate_bio(parsed)
        if bio:
            parsed.bio = bio
        return parsed

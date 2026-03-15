from __future__ import annotations

from functools import lru_cache

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from ai.config import get_ai_settings
from ai.prompts.resume_prompt import RESUME_EXTRACTION_SYSTEM
from ai.schemas import ResumeParsedResponse


@lru_cache
def get_resume_extraction_chain():
    settings = get_ai_settings()
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=settings.GROQ_TEMPERATURE,
    )

    parser = PydanticOutputParser(pydantic_object=ResumeParsedResponse)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RESUME_EXTRACTION_SYSTEM),
            (
                "human",
                "Resume text:\n{resume_text}\n\n{format_instructions}",
            ),
        ]
    )

    # Normal path: return Pydantic object.
    chain = prompt | llm | parser

    # Fallback path (see ResumeParserService): return raw text if force_text is True.
    text_chain = prompt | llm | StrOutputParser()

    class _Switch:
        def invoke(self, inp: dict):
            payload = dict(inp)
            payload.setdefault("format_instructions", format_instructions)
            if payload.pop("force_text", False):
                return text_chain.invoke(payload)
            return chain.invoke(payload)

    return _Switch()

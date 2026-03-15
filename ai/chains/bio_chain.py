from __future__ import annotations

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from ai.config import get_ai_settings
from ai.prompts.bio_prompt import BIO_SYSTEM


@lru_cache
def get_bio_generation_chain():
    settings = get_ai_settings()
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", BIO_SYSTEM),
            (
                "human",
                "Extracted resume JSON (may include empty fields):\n{extracted}\n\nWrite a 2–4 sentence professional bio.",
            ),
        ]
    )

    return prompt | llm | StrOutputParser()

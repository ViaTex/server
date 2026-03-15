from __future__ import annotations

import anyio

from ai.chains.bio_chain import get_bio_generation_chain
from ai.schemas import ResumeParsedResponse


class BioGeneratorService:
    async def generate_bio(self, parsed: ResumeParsedResponse) -> str:
        chain = get_bio_generation_chain()
        payload = parsed.model_dump()

        # Use threadpool because most LangChain LLM clients are sync.
        bio: str = await anyio.to_thread.run_sync(
            lambda: chain.invoke({"extracted": payload})
        )
        return (bio or "").strip()

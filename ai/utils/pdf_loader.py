from __future__ import annotations

import io

import pdfplumber


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        return ""

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        chunks: list[str] = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
        return "\n\n".join(chunks)

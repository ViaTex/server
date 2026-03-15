from __future__ import annotations

import re


_NULLS = re.compile(r"\x00+")
_MULTI_WS = re.compile(r"[ \t\f\v]+")
_MULTI_NL = re.compile(r"\n{3,}")


def clean_resume_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _NULLS.sub("", text)
    text = _MULTI_WS.sub(" ", text)
    # Keep newlines (helps sectioning), but avoid huge blank gaps
    text = _MULTI_NL.sub("\n\n", text)
    return text.strip()

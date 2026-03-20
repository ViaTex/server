from __future__ import annotations

from app.ai.evaluator import generate_chat_completion
from app.models.user import Student


def generate_section_question(
    *,
    section_type: str,
    student: Student,
    prior_context: str | None = None,
) -> str:
    system_prompt = (
        "You are an exam generator for a multi-stage skills assessment. "
        "Return ONLY the question text without extra commentary or formatting."
    )

    profile_summary = (
        f"Student profile: name={student.name}, "
        f"skills={student.technical_skills or ''}, "
        f"soft_skills={student.soft_skills or ''}, "
        f"experience={student.experience or []}."
    )

    context_block = f"Prior context: {prior_context}" if prior_context else "Prior context: None"

    user_prompt = (
        f"Section type: {section_type}.\n"
        f"{profile_summary}\n"
        f"{context_block}\n"
        "Generate a concise, challenging question aligned to the section type."
    )

    question = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=220,
    )

    return question.strip() or "Please respond to the prompt for this section."

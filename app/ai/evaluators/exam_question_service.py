from __future__ import annotations

import json

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


def _extract_json_object(raw_text: str) -> dict:
    if not raw_text:
        return {}
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    snippet = raw_text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return {}


def _validate_section_b_payload(payload: dict) -> None:
    mcqs = payload.get("mcqs")
    long_questions = payload.get("long_questions")
    if not isinstance(mcqs, list) or not isinstance(long_questions, list):
        raise ValueError("Invalid Section B payload")
    if len(mcqs) != 15 or len(long_questions) != 5:
        raise ValueError("Section B must include exactly 15 MCQs and 5 long questions")

    seen_mcq_ids = set()
    for item in mcqs:
        if not isinstance(item, dict):
            raise ValueError("Invalid MCQ payload")
        mcq_id = item.get("id")
        question = item.get("question")
        options = item.get("options")
        correct = item.get("correct_option")
        if not mcq_id or not question or not isinstance(options, list):
            raise ValueError("Invalid MCQ payload")
        if len(options) != 4 or not all(isinstance(opt, str) for opt in options):
            raise ValueError("Each MCQ must include 4 string options")
        if correct not in options:
            raise ValueError("MCQ correct_option must be one of the options")
        if mcq_id in seen_mcq_ids:
            raise ValueError("Duplicate MCQ id")
        seen_mcq_ids.add(mcq_id)

    seen_long_ids = set()
    for item in long_questions:
        if not isinstance(item, dict):
            raise ValueError("Invalid long question payload")
        long_id = item.get("id")
        question = item.get("question")
        if not long_id or not question:
            raise ValueError("Invalid long question payload")
        if long_id in seen_long_ids:
            raise ValueError("Duplicate long question id")
        seen_long_ids.add(long_id)


def generate_section_b_questions(*, student: Student) -> tuple[dict, dict]:
    system_prompt = (
        "You are an exam generator for Section B fundamentals. "
        "Return ONLY valid JSON with schema: "
        "{\"mcqs\":[{" \
        "\"id\":\"q1\",\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"correct_option\":\"B\"}"
        "]," \
        "\"long_questions\":[{" \
        "\"id\":\"l1\",\"question\":\"...\"}]}" \
        " with exactly 15 MCQs and 5 long questions."
    )

    profile_summary = (
        f"Student profile: name={student.name}, "
        f"skills={student.technical_skills or ''}, "
        f"soft_skills={student.soft_skills or ''}, "
        f"experience={student.experience or []}."
    )

    user_prompt = (
        f"{profile_summary}\n"
        "Generate Section B fundamentals: 15 MCQs with 4 options each, "
        "and 5 long descriptive questions. Ensure unique ids q1-q15 and l1-l5."
    )

    raw = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=1200,
    )

    payload = {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = _extract_json_object(raw)

    _validate_section_b_payload(payload)

    public_payload = {
        "mcqs": [
            {
                "id": item["id"],
                "question": item["question"],
                "options": item["options"],
            }
            for item in payload["mcqs"]
        ],
        "long_questions": [
            {
                "id": item["id"],
                "question": item["question"],
            }
            for item in payload["long_questions"]
        ],
    }

    answer_key = {
        "mcq_answers": {
            item["id"]: item["correct_option"] for item in payload["mcqs"]
        }
    }

    return public_payload, answer_key

from __future__ import annotations

import json
import uuid

from app.ai.utils.logger import ai_error

from app.ai.evaluator import generate_chat_completion
from app.models.user import Student


def generate_section_question(
    *,
    section_type: str,
    student: Student,
    prior_context: str | None = None,
) -> dict:
    system_prompt = (
        "You are an exam generator for a multi-stage skills assessment. "
        "Return ONLY valid JSON with schema: "
        "{\"prompt_text\": \"<The coding or debugging scenario text>\", \"topics\": [\"<topic1>\", \"<topic2>\"]}."
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
        "Generate a concise, challenging question aligned to the section type and return structured JSON."
    )

    raw_text = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=300,
    )

    payload = _parse_json_response(raw_text)
    if not isinstance(payload, dict):
        payload = {"prompt_text": raw_text.strip() or "Please respond to the prompt for this section.", "topics": []}
    
    if not payload.get("prompt_text"):
        payload["prompt_text"] = "Please respond to the prompt for this section."
    
    if not isinstance(payload.get("topics"), list):
        payload["topics"] = []
        
    return payload


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


def _parse_json_response(raw_text: str) -> dict:
    if not raw_text:
        return {}
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _extract_json_object(cleaned)


def _fallback_section_b_payload() -> tuple[dict, dict]:
    mcqs = []
    for idx in range(1, 16):
        mcqs.append(
            {
                "id": str(uuid.uuid4()),
                "question": f"Fundamentals check {idx}: choose the best answer.",
                "options": ["A", "B", "C", "D"],
                "correct_option": "A",
            }
        )

    long_questions = []
    for idx in range(1, 6):
        long_questions.append(
            {
                "id": str(uuid.uuid4()),
                "question": f"Explain your reasoning for concept {idx} with a real-world example.",
            }
        )

    public_payload = {
        "mcqs": [
            {"id": item["id"], "question": item["question"], "options": item["options"]}
            for item in mcqs
        ],
        "long_questions": long_questions,
        "topics": [],
    }
    answer_key = {"mcq_answers": {item["id"]: item["correct_option"] for item in mcqs}}
    return public_payload, answer_key


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


def _normalize_mcq_item(item: dict) -> dict:
    mcq_id = item.get("id") or str(uuid.uuid4())
    question = item.get("question")
    options = item.get("options")
    correct = item.get("correct_option")

    if isinstance(options, dict):
        options = list(options.values())
    elif isinstance(options, list) and options and isinstance(options[0], dict):
        options = [opt.get("text") or opt.get("option") or "" for opt in options]

    options = [str(opt).strip() for opt in (options or []) if str(opt).strip()]
    options = options[:4]

    if isinstance(correct, int) and 0 <= correct < len(options):
        correct = options[correct]
    elif isinstance(correct, str):
        letter = correct.strip().upper()
        if letter in ("A", "B", "C", "D"):
            index = ["A", "B", "C", "D"].index(letter)
            if index < len(options):
                correct = options[index]

    return {
        "id": mcq_id,
        "question": question,
        "options": options,
        "correct_option": correct,
    }


def _normalize_section_b_payload(payload: dict) -> dict:
    mcqs = payload.get("mcqs") if isinstance(payload.get("mcqs"), list) else []
    long_questions = payload.get("long_questions") if isinstance(payload.get("long_questions"), list) else []

    normalized_mcqs = []
    for item in mcqs:
        if not isinstance(item, dict):
            continue
        normalized_mcqs.append(_normalize_mcq_item(item))

    normalized_long = []
    for item in long_questions:
        if not isinstance(item, dict):
            continue
        normalized_long.append(
            {
                "id": item.get("id") or str(uuid.uuid4()),
                "question": item.get("question"),
            }
        )

    topics = payload.get("topics") if isinstance(payload.get("topics"), list) else []
    topics = [t for t in topics if isinstance(t, str)]

    return {
        "mcqs": normalized_mcqs,
        "long_questions": normalized_long,
        "topics": topics,
    }


def generate_section_b_questions(*, student: Student) -> tuple[dict, dict]:
    profile_summary = (
        f"Student profile: name={student.name}, "
        f"skills={student.technical_skills or ''}, "
        f"soft_skills={student.soft_skills or ''}, "
        f"experience={student.experience or []}."
    )

    base_system_prompt = (
        "You are an exam generator for Section B fundamentals. "
        "Return ONLY valid JSON with schema: "
        "{\"mcqs\":[{" \
        "\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"correct_option\":\"B\"}"
        "]," \
        "\"long_questions\":[{" \
        "\"question\":\"...\"}]," \
        "\"topics\":[\"...\"]}" \
        " with exactly 15 MCQs and 5 long questions. "
        "Each MCQ must include correct_option and it must be one of the options. "
        "Do not include markdown or explanations."
    )

    user_prompt = (
        f"{profile_summary}\n"
        "Generate Section B fundamentals: 15 MCQs with 4 options each, "
        "and 5 long descriptive questions. Also generate a topics array containing relevant technical topics. "
        "Return options as plain strings and include correct_option for every MCQ."
    )

    last_error = ""
    payload: dict = {}
    for attempt in range(3):
        system_prompt = base_system_prompt
        if attempt == 1:
            system_prompt += " Your response MUST be valid JSON only."
        if attempt == 2:
            system_prompt += " Return minified JSON with no code fences and no extra keys."
        raw = generate_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.05,
            max_tokens=1400,
        )
        payload = _parse_json_response(raw)
        payload = _normalize_section_b_payload(payload)
        try:
            _validate_section_b_payload(payload)
            last_error = ""
            break
        except ValueError as exc:
            last_error = str(exc)
            payload = {}

    if last_error:
        ai_error(f"Section B generation failed validation: {last_error}. Using fallback questions.")
        return _fallback_section_b_payload()

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
        "topics": payload.get("topics", []),
    }

    answer_key = {
        "mcq_answers": {
            item["id"]: item["correct_option"] for item in payload["mcqs"]
        }
    }

    return public_payload, answer_key

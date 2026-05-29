from __future__ import annotations

import json
import uuid

from app.ai.embeddings.generator import generate_embedding
from app.ai.evaluator import generate_chat_completion, download_media, transcribe_media
from app.ai.utils.logger import ai_error, ai_log
from app.ai.utils.topic_cache import get_global_topics, update_global_topics
from app.core.database import SessionLocal
from app.models.exam_response import ExamResponse
from app.services.exam_response_service import update_response_ai_analysis


SECTION_D_FIXED_TOPICS = ["Problem Solving Skill", "Verbal Explanation", "Confidence"]


def _extract_json_object(raw_text: str) -> dict | None:
    if not raw_text:
        return None
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = raw_text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def _coerce_score(value: object, default: float = 5.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(1.0, min(10.0, score))


def _extract_prompt_text(question_text: str) -> str:
    if not question_text:
        return ""
    try:
        payload = json.loads(question_text)
    except json.JSONDecodeError:
        return question_text

    if isinstance(payload, dict):
        prompt_text = payload.get("prompt_text")
        if isinstance(prompt_text, str) and prompt_text.strip():
            return prompt_text
    return question_text


def generate_expert_answer(*, question_text: str) -> str:
    system_prompt = (
        "You are a senior engineer. Provide the ideal explanation or fix for the debugging prompt. "
        "Return ONLY the explanation text without extra formatting."
    )
    user_prompt = f"Debugging prompt:\n{question_text}\nProvide the correct solution explanation."

    return generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=320,
    )


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    return float(sum(a * b for a, b in zip(vec_a, vec_b)))


def score_debug_transcript(*, question_text: str, transcript: str) -> dict:
    expert_answer = generate_expert_answer(question_text=question_text)
    expert_embedding = generate_embedding(expert_answer)
    transcript_embedding = generate_embedding(transcript)

    similarity = cosine_similarity(expert_embedding, transcript_embedding)
    similarity = max(0.0, min(1.0, similarity))
    score_value = max(1.0, min(10.0, round(similarity * 10, 2)))

    return {
        "score": score_value,
        "expert_answer": expert_answer,
        "similarity": similarity,
    }


def _evaluate_section_d_topics(*, transcript: str, global_topics: list[str]) -> dict:
    topics_text = ", ".join(global_topics) if global_topics else "(none)"
    system_prompt = (
        "You are evaluating a debugging interview transcript. Score ONLY these fixed topics: "
        f"{SECTION_D_FIXED_TOPICS}. Also generate 1-2 technical topics based on the transcript. "
        "RAG topics list (use exact matches first): "
        f"{topics_text}. "
        "If creating a new topic, use Title Case, no symbols, no acronyms unless a 3-letter tech, "
        "and maximum 3 words. Return ONLY JSON matching this schema: "
        "{\"topic_scores\": {\"<fixed/technical topic>\": <1-10>}, "
        "\"new_topics\": [\"<topic>\", \"<topic>\"]}."
    )
    user_prompt = f"Transcript:\n{transcript}"

    raw_text = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=360,
    )

    payload = None
    if raw_text:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = _extract_json_object(raw_text)

    if not isinstance(payload, dict):
        payload = {}

    topic_scores = payload.get("topic_scores") if isinstance(payload.get("topic_scores"), dict) else {}
    new_topics = payload.get("new_topics") if isinstance(payload.get("new_topics"), list) else []
    new_topics = [topic for topic in new_topics if isinstance(topic, str) and topic.strip()]

    normalized_scores = {}
    for topic in SECTION_D_FIXED_TOPICS:
        normalized_scores[topic] = _coerce_score(topic_scores.get(topic))

    for topic, value in topic_scores.items():
        if not isinstance(topic, str):
            continue
        cleaned_topic = topic.strip()
        if not cleaned_topic or cleaned_topic in normalized_scores:
            continue
        normalized_scores[cleaned_topic] = _coerce_score(value)

    return {
        "topic_scores": normalized_scores,
        "new_topics": new_topics,
    }


def process_section_d_debug_ai(response_id: str, video_url: str) -> None:
    """Transcribe Section D video and score against an expert answer."""
    db = SessionLocal()
    try:
        response_uuid = uuid.UUID(str(response_id))
        ai_log(f"Section D AI evaluation started for response_id={response_id}")

        response = db.query(ExamResponse).filter(ExamResponse.id == response_uuid).first()
        if not response:
            raise ValueError("Exam response not found")

        media_bytes = download_media(video_url)
        transcript = transcribe_media(media_bytes, filename="section_d_debug.mp4")
        prompt_text = _extract_prompt_text(response.question_text)
        score_analysis = score_debug_transcript(question_text=prompt_text, transcript=transcript)

        global_topics = get_global_topics()
        topic_payload = _evaluate_section_d_topics(transcript=transcript, global_topics=global_topics)
        if topic_payload.get("new_topics"):
            update_global_topics(topic_payload.get("new_topics"))

        score_value = float(score_analysis.get("score") or 0.0)
        hints_used = float(response.hints_used or 0)
        score_value = max(score_value - (hints_used * 0.5), 0.0)

        analysis = {
            "score": score_value,
            "feedback": {
                "topic_scores": topic_payload.get("topic_scores", {}),
                "expert_answer": score_analysis.get("expert_answer"),
                "similarity": score_analysis.get("similarity"),
            },
        }

        update_response_ai_analysis(
            db,
            response=response,
            transcript=transcript,
            ai_analysis=analysis,
        )
        ai_log(f"Section D AI evaluation completed for response_id={response_id}")
    except Exception as exc:
        ai_error(f"Section D AI evaluation failed for response_id={response_id}: {exc}")
    finally:
        db.close()

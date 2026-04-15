from __future__ import annotations

import json
import uuid

from app.ai.embeddings.generator import generate_embedding
from app.ai.evaluator import analyze_transcript, generate_chat_completion, download_media, transcribe_media
from app.ai.utils.topic_cache import get_global_topics, sanitize_topics, update_global_topics
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal
from app.models.exam_response import ExamResponse
from app.services.exam_response_service import update_response_ai_analysis


SECTION_D_FIXED_TOPICS = ["Problem Solving Skill", "Verbal Explanation", "Confidence"]


def _extract_prompt_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text
    if isinstance(parsed, dict) and parsed.get("prompt_text"):
        return str(parsed.get("prompt_text"))
    return raw_text


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


def _analyze_section_d_transcript(transcript: str) -> tuple[dict, list[str]]:
    global_topics = get_global_topics()
    system_prompt = (
        "You are an expert technical interviewer and behavioral analyst. "
        "Evaluate the transcript for Section D (debugging explanation). "
        "Use the provided global topics list first with exact matches. "
        "If new topics are necessary, add 1-2 only, Title Case, no symbols, no acronyms, max 3 words. "
        "Return ONLY valid JSON with schema: "
        "{\"feedback\": {"
        "\"strengths\": [..], "
        "\"areas_for_improvement\": [..], "
        "\"behavioral_analysis\": \"...\"}, "
        "\"topics\": [..]}."
    )
    user_prompt = (
        f"Fixed topics: {SECTION_D_FIXED_TOPICS}\n"
        f"Global topics: {global_topics}\n"
        f"Transcript:\n{transcript}"
    )

    raw = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=420,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    feedback = data.get("feedback") if isinstance(data.get("feedback"), dict) else {}
    strengths = feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else []
    areas = feedback.get("areas_for_improvement") if isinstance(feedback.get("areas_for_improvement"), list) else []
    behavioral = feedback.get("behavioral_analysis")

    if not strengths or not areas or not isinstance(behavioral, str):
        fallback = analyze_transcript(transcript)
        feedback = fallback.get("feedback", {}) if isinstance(fallback.get("feedback"), dict) else {}
        strengths = feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else []
        areas = feedback.get("areas_for_improvement") if isinstance(feedback.get("areas_for_improvement"), list) else []
        behavioral = feedback.get("behavioral_analysis")
        topics = SECTION_D_FIXED_TOPICS[:]
        return {
            "strengths": strengths,
            "areas_for_improvement": areas,
            "behavioral_analysis": behavioral,
        }, topics

    topics_raw = data.get("topics") if isinstance(data.get("topics"), list) else []
    topics_clean = sanitize_topics(topics_raw)

    merged_topics = SECTION_D_FIXED_TOPICS[:]
    for topic in topics_clean:
        if topic in global_topics and topic not in merged_topics:
            merged_topics.append(topic)

    new_topics = []
    for topic in topics_clean:
        if topic not in global_topics and topic not in merged_topics:
            new_topics.append(topic)
    new_topics = new_topics[:2]

    if new_topics:
        update_global_topics(new_topics)
        merged_topics.extend(new_topics)

    strengths = [item for item in strengths if isinstance(item, str) and item.strip()][:3]
    areas = [item for item in areas if isinstance(item, str) and item.strip()][:3]
    if not isinstance(behavioral, str) or not behavioral.strip():
        behavioral = "The response shows mixed clarity and needs more structured delivery."

    return {
        "strengths": strengths,
        "areas_for_improvement": areas,
        "behavioral_analysis": behavioral,
    }, merged_topics


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
        feedback_analysis, topics = _analyze_section_d_transcript(transcript)
        score_value = score_analysis.get("score")
        hints_used = int(response.hints_used or 0)
        if score_value is not None and hints_used:
            score_value = max(float(score_value) - (0.5 * hints_used), 0.0)

        analysis = {
            "score": score_value,
            "feedback": {
                **(feedback_analysis or {}),
                "topics": topics,
            },
            "expert_answer": score_analysis.get("expert_answer"),
            "similarity": score_analysis.get("similarity"),
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

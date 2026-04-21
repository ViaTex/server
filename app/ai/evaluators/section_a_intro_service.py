import json
import uuid

from app.ai.evaluator import download_media, generate_chat_completion, transcribe_media
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal
from app.models.exam_response import ExamResponse
from app.services.exam_response_service import update_response_ai_analysis


SECTION_A_TOPICS = ["Confidence", "Communication", "Professionalism", "Clarity"]


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


def _evaluate_section_a_transcript(transcript: str) -> dict:
    system_prompt = (
        "You are an interview evaluator. You must ONLY score these topics: "
        f"{SECTION_A_TOPICS}. You are strictly forbidden from creating or extracting any new topics. "
        "Return ONLY JSON matching this schema: "
        "{\"score\": <number 1-10>, "
        "\"topic_scores\": {\"Confidence\": <1-10>, \"Communication\": <1-10>, "
        "\"Professionalism\": <1-10>, \"Clarity\": <1-10>}, "
        "\"strengths\": [..], \"areas_for_improvement\": [..]}."
    )
    user_prompt = f"Transcript:\n{transcript}"

    raw_text = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=320,
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
    normalized_scores = {}
    for topic in SECTION_A_TOPICS:
        normalized_scores[topic] = _coerce_score(topic_scores.get(topic))

    strengths = payload.get("strengths") if isinstance(payload.get("strengths"), list) else []
    areas = payload.get("areas_for_improvement") if isinstance(payload.get("areas_for_improvement"), list) else []
    strengths = [item for item in strengths if isinstance(item, str) and item.strip()][:3]
    areas = [item for item in areas if isinstance(item, str) and item.strip()][:3]

    score_value = _coerce_score(payload.get("score"), default=sum(normalized_scores.values()) / len(normalized_scores))

    return {
        "score": round(score_value, 2),
        "feedback": {
            "topic_scores": normalized_scores,
            "strengths": strengths,
            "areas_for_improvement": areas,
        },
    }


def process_section_a_intro_ai(response_id: str, video_url: str) -> None:
    """Run transcription + analysis for Section A and persist results."""
    db = SessionLocal()
    try:
        response_uuid = uuid.UUID(str(response_id))
        ai_log(f"Section A AI evaluation started for response_id={response_id}")

        response = db.query(ExamResponse).filter(ExamResponse.id == response_uuid).first()
        if not response:
            raise ValueError("Exam response not found")

        media_bytes = download_media(video_url)
        transcript = transcribe_media(media_bytes, filename="section_a_intro.mp4")
        analysis = _evaluate_section_a_transcript(transcript)

        update_response_ai_analysis(
            db,
            response=response,
            transcript=transcript,
            ai_analysis=analysis,
        )
        ai_log(f"Section A AI evaluation completed for response_id={response_id}")
    except Exception as exc:
        ai_error(f"Section A AI evaluation failed for response_id={response_id}: {exc}")
    finally:
        db.close()

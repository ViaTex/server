import json
import uuid

from app.ai.evaluator import analyze_transcript, download_media, generate_chat_completion, transcribe_media
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal
from app.models.exam_response import ExamResponse
from app.services.exam_response_service import update_response_ai_analysis


SECTION_A_TOPICS = ["Confidence", "Communication", "Professionalism", "Clarity"]


def _analyze_section_a_transcript(transcript: str) -> dict:
    system_prompt = (
        "You are an expert technical recruiter and behavioral analyst. "
        "Evaluate the transcript for Section A (self-introduction). "
        "You MUST use the provided topics list exactly and never add new topics. "
        "Return ONLY valid JSON with schema: "
        "{\"score\": <number 1-10>, "
        "\"feedback\": {"
        "\"strengths\": [..], "
        "\"areas_for_improvement\": [..], "
        "\"behavioral_analysis\": \"...\", "
        "\"topics\": [..]}}."
    )
    user_prompt = (
        f"Allowed topics: {SECTION_A_TOPICS}\n"
        f"Transcript:\n{transcript}"
    )

    raw = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=400,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    score = data.get("score")
    try:
        score_value = float(score)
    except (TypeError, ValueError):
        score_value = None

    feedback = data.get("feedback") if isinstance(data.get("feedback"), dict) else {}
    strengths = feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else []
    areas = feedback.get("areas_for_improvement") if isinstance(feedback.get("areas_for_improvement"), list) else []
    behavioral = feedback.get("behavioral_analysis")

    if score_value is None or not strengths or not areas or not isinstance(behavioral, str):
        fallback = analyze_transcript(transcript)
        feedback = fallback.get("feedback", {}) if isinstance(fallback.get("feedback"), dict) else {}
        score_value = float(fallback.get("score", 5.0))
        strengths = feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else []
        areas = feedback.get("areas_for_improvement") if isinstance(feedback.get("areas_for_improvement"), list) else []
        behavioral = feedback.get("behavioral_analysis")

    score_value = max(1.0, min(10.0, float(score_value)))
    strengths = [item for item in strengths if isinstance(item, str) and item.strip()][:3]
    areas = [item for item in areas if isinstance(item, str) and item.strip()][:3]
    if not isinstance(behavioral, str) or not behavioral.strip():
        behavioral = "The response shows mixed clarity and needs more structured delivery."

    return {
        "score": round(score_value, 2),
        "feedback": {
            "strengths": strengths,
            "areas_for_improvement": areas,
            "behavioral_analysis": behavioral,
            "topics": SECTION_A_TOPICS,
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
        analysis = _analyze_section_a_transcript(transcript)

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

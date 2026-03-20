from __future__ import annotations

import uuid

from app.ai.embeddings.generator import generate_embedding
from app.ai.evaluator import generate_chat_completion, download_media, transcribe_media
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal
from app.models.exam_response import ExamResponse
from app.services.exam_response_service import update_response_ai_analysis
from app.services.exam_session_service import update_exam_scores_from_responses


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
        analysis = score_debug_transcript(question_text=response.question_text, transcript=transcript)

        update_response_ai_analysis(
            db,
            response=response,
            transcript=transcript,
            ai_analysis=analysis,
        )
        update_exam_scores_from_responses(db, session=response.session)
        ai_log(f"Section D AI evaluation completed for response_id={response_id}")
    except Exception as exc:
        ai_error(f"Section D AI evaluation failed for response_id={response_id}: {exc}")
    finally:
        db.close()

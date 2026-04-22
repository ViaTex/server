import uuid

from app.ai.evaluate import evaluate_section_a_transcript
from app.ai.evaluator import download_media, transcribe_media
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal
from app.models.exam_response import ExamResponse
from app.services.exam_response_service import update_response_ai_analysis


SECTION_A_TOPICS = ["Confidence", "Communication", "Professionalism", "Clarity"]


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
        analysis = evaluate_section_a_transcript(transcript, SECTION_A_TOPICS)

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

import uuid

from app.ai.evaluator import analyze_transcript, download_media, transcribe_media
from app.ai.utils.logger import ai_error, ai_log
from app.core.database import SessionLocal
from app.services.exam_session_service import update_section_a_intro_ai_analysis


def process_section_a_intro_ai(exam_session_id: str, video_url: str) -> None:
    """Run transcription + analysis for Section A and persist results."""
    db = SessionLocal()
    try:
        exam_uuid = uuid.UUID(str(exam_session_id))
        ai_log(f"Section A AI evaluation started for exam_session_id={exam_session_id}")

        media_bytes = download_media(video_url)
        transcript = transcribe_media(media_bytes, filename="section_a_intro.mp4")
        analysis = analyze_transcript(transcript)

        update_section_a_intro_ai_analysis(
            db,
            exam_session_id=exam_uuid,
            transcript=transcript,
            ai_analysis=analysis,
        )
        ai_log(f"Section A AI evaluation completed for exam_session_id={exam_session_id}")
    except Exception as exc:
        ai_error(f"Section A AI evaluation failed for exam_session_id={exam_session_id}: {exc}")
    finally:
        db.close()

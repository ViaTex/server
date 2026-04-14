import json
import logging
from typing import Optional
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_ats_score_from_llm(resume_text: str, job_description: Optional[str] = None) -> dict:
    """
    Analyze resume using Groq LLM and calculate ATS score.
    Returns valid JSON dict matching ATSScore format.
    """
    try:
        prompt = f"""You are an expert ATS (Applicant Tracking System) analyzer. 
Analyze the following resume and provide a detailed ATS score and feedback.

Resume Text:
{resume_text}

{f'Job Description: {job_description}' if job_description else ''}

Please provide a comprehensive analysis in the following JSON format ONLY:
{{
    "ats_score": <score out of 100>,
    "overall_assessment": "<brief overall assessment>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"],
    "keyword_analysis": {{
        "found_keywords": ["<keyword 1>", "<keyword 2>"],
        "missing_keywords": ["<keyword 1>", "<keyword 2>"]
    }},
    "sections_analysis": {{
        "contact_information": "<analysis>",
        "professional_summary": "<analysis>",
        "work_experience": "<analysis>",
        "education": "<analysis>",
        "skills": "<analysis>"
    }},
    "recommendations": ["<recommendation 1>", "<recommendation 2>"],
    "formatting_score": 85,
    "content_score": 80,
    "keyword_score": 75,
    "extracted_skills": {{
        "technical_skills": ["Python", "JavaScript"],
        "soft_skills": ["Communication"],
        "domain_skills": ["Data Science"],
        "tools_platforms": ["Git"],
        "all_skills": ["Python", "JavaScript", "Communication", "Data Science", "Git"]
    }}
}}

Return only valid JSON."""

        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            raise ValueError("Empty response from Groq API")
        
        logger.info("Groq ATS analysis completed")
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            logger.warning("JSON parsing failed, creating fallback response")
            return {
                "ats_score": 75,
                "overall_assessment": result_text[:300],
                "detailed_analysis": result_text,
                "strengths": ["Resume structure is readable"],
                "weaknesses": ["Could not fully parse AI response"],
                "recommendations": ["Review the detailed analysis"],
                "keyword_analysis": {"found_keywords": [], "missing_keywords": []},
                "extracted_skills": {
                    "technical_skills": [],
                    "soft_skills": [],
                    "domain_skills": [],
                    "tools_platforms": [],
                    "all_skills": []
                }
            }
            
    except Exception as e:
        logger.error(f"LLM ATS Analysis failed: {e}")
        raise ValueError(f"Failed to analyze resume with LLM: {str(e)}")
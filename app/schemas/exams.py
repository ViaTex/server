from pydantic import BaseModel, Field


class MentorFeedback(BaseModel):
    strengths: list[str] = Field(..., description="Key strengths observed in the response")
    behavioral_analysis: str = Field(..., description="Behavioral analysis summary")
    areas_for_improvement: list[str] = Field(..., description="Specific improvement areas")

from pydantic import BaseModel, Field

from app.schemas.job import JobStructured


class MatchReport(BaseModel):
    job_id: int | None = None
    job: JobStructured | None = None
    skill_score: float = 0
    project_score: float = 0
    constraint_score: float = 0
    direction_score: float = 0
    preparation_score: float = 0
    overall_score: float = 0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendation: str = ""
    resume_suggestions: list[str] = Field(default_factory=list)
    preparation_suggestions: list[str] = Field(default_factory=list)
    score_details: dict[str, str] = Field(default_factory=dict)
    llm_used: bool = False
    llm_notes: str = ""

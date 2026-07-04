from pydantic import BaseModel, Field


class InterviewPrepReport(BaseModel):
    job_id: int
    technical_questions: list[str] = Field(default_factory=list)
    project_questions: list[str] = Field(default_factory=list)
    followup_questions: list[str] = Field(default_factory=list)
    answer_points: list[str] = Field(default_factory=list)
    review_plan: list[str] = Field(default_factory=list)
    self_intro_tip: str = ""


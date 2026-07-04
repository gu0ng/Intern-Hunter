from pydantic import BaseModel, Field


class JobStructured(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    job_type: str = ""
    category: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    bonus_skills: list[str] = Field(default_factory=list)
    degree_requirement: str = ""
    graduation_requirement: str = ""
    intern_duration: str = ""
    keywords: list[str] = Field(default_factory=list)
    risk_notes: str = ""
    summary: str = ""
    url: str = ""


class JobMatchRequest(BaseModel):
    jd_text: str


class JobRecord(BaseModel):
    id: int
    company: str
    title: str
    location: str
    job_type: str
    category: str
    overall_score: float | None = None
    status: str | None = None


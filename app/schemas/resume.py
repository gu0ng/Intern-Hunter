from pydantic import BaseModel, Field


class ResumeProject(BaseModel):
    name: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    name: str = ""
    education: str = ""
    major: str = ""
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    internships: list[str] = Field(default_factory=list)
    research_direction: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    city_preference: list[str] = Field(default_factory=list)
    availability: str = ""
    raw_text_summary: str = ""
    parse_source: str = "manual"


class ResumeParseResult(BaseModel):
    profile: ResumeProfile
    raw_text: str
    saved: bool = False
    llm_used: bool = False
    fallback_reason: str = ""

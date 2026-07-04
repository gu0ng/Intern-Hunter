from typing import TypedDict

from app.schemas.job import JobStructured
from app.schemas.match import MatchReport
from app.schemas.resume import ResumeProfile


class JobMatchState(TypedDict, total=False):
    jd_text: str
    jd_hash: str
    resume_path: str | None
    persist: bool
    cached: bool
    cache_hit: str
    job: JobStructured
    resume: ResumeProfile
    report: MatchReport

from sqlalchemy.orm import Session

from app.db import crud
from app.schemas.job import JobAnalyzeResult
from app.services.jd_parser import parse_jd
from app.tools.cache_tool import JobCacheTool
from app.tools.hash_utils import compute_jd_hash


def analyze_and_save_job(db: Session, jd_text: str) -> JobAnalyzeResult:
    jd_hash = compute_jd_hash(jd_text)
    cache = JobCacheTool()

    cached_job_id = cache.get_job_id(jd_hash)
    if cached_job_id is not None:
        cached_job = crud.get_job_structured(db, cached_job_id)
        if cached_job:
            return JobAnalyzeResult(job_id=cached_job_id, job=cached_job, cached=True, cache_hit="redis")

    existing = crud.get_job_by_jd_hash(db, jd_hash)
    if existing:
        cache.set_job_id(jd_hash, existing.id)
        return JobAnalyzeResult(job_id=existing.id, job=crud.get_job_structured(db, existing.id), cached=True, cache_hit="sqlite")

    job = parse_jd(jd_text)
    db_job = crud.create_job(db, jd_text, job, jd_hash=jd_hash)
    cache.set_job_id(jd_hash, db_job.id)
    return JobAnalyzeResult(job_id=db_job.id, job=job, cached=False, cache_hit="miss")

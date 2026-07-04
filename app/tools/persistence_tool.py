from sqlalchemy.orm import Session

from app.db.crud import create_job_with_report, get_latest_match_report, get_latest_match_report_by_jd_hash
from app.schemas.job import JobStructured
from app.schemas.match import MatchReport
from app.tools.cache_tool import JobCacheTool
from app.tools.hash_utils import compute_jd_hash


class PersistenceTool:
    name = "persistence_tool"
    description = "Persist job matches with Redis cache and SQLite jd_hash deduplication."

    def __init__(self) -> None:
        self.cache = JobCacheTool()

    def save_job_match(self, db: Session, jd_text: str, job: JobStructured, report: MatchReport) -> MatchReport:
        jd_hash = compute_jd_hash(jd_text)

        cached_job_id = self.cache.get_job_id(jd_hash)
        if cached_job_id is not None:
            cached_report = get_latest_match_report(db, cached_job_id)
            if cached_report:
                cached_report.llm_notes = _append_note(cached_report.llm_notes, "命中 Redis 缓存，未重复保存岗位。")
                cached_report.score_details["cache_hit"] = "redis"
                return cached_report

        existing_report = get_latest_match_report_by_jd_hash(db, jd_hash)
        if existing_report:
            if existing_report.job_id is not None:
                self.cache.set_job_id(jd_hash, existing_report.job_id)
            existing_report.llm_notes = _append_note(existing_report.llm_notes, "命中 SQLite 去重，未重复保存岗位。")
            existing_report.score_details["cache_hit"] = "sqlite"
            return existing_report

        saved_report = create_job_with_report(db, jd_text, job, report, jd_hash=jd_hash)
        if saved_report.job_id is not None:
            self.cache.set_job_id(jd_hash, saved_report.job_id)
        saved_report.score_details["cache_hit"] = "miss"
        return saved_report


def _append_note(current: str, note: str) -> str:
    return f"{current} {note}".strip() if current else note

from sqlalchemy.orm import Session

from app.db.crud import create_job_with_report
from app.schemas.job import JobStructured
from app.schemas.match import MatchReport


class PersistenceTool:
    name = "persistence_tool"
    description = "Persist structured jobs, match reports, and default application state to SQLite."

    def save_job_match(self, db: Session, jd_text: str, job: JobStructured, report: MatchReport) -> MatchReport:
        return create_job_with_report(db, jd_text, job, report)

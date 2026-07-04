from app.db.crud import get_job_structured, save_interview_prep
from app.db.database import SessionLocal, init_db
from app.schemas.interview import InterviewPrepReport
from app.services.interview_generator import generate_interview_prep
from app.services.resume_profiler import load_resume_profile


def run_interview_agent(job_id: int, persist: bool = True) -> InterviewPrepReport:
    init_db()
    with SessionLocal() as db:
        job = get_job_structured(db, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        profile = load_resume_profile()
        report = generate_interview_prep(job_id, job, profile)
        if persist:
            save_interview_prep(db, report)
        return report


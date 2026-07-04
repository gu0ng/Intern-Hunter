from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.graph_job_match import run_job_match_agent
from app.db import crud
from app.db.database import get_db
from app.schemas.job import JobMatchRequest
from app.schemas.match import MatchReport


router = APIRouter(prefix="/match", tags=["match"])


@router.post("/run", response_model=MatchReport)
def run_match(request: JobMatchRequest):
    return run_job_match_agent(request.jd_text, persist=True)


@router.get("/{job_id}", response_model=MatchReport)
def get_match_report(job_id: int, db: Session = Depends(get_db)):
    report = crud.get_latest_match_report(db, job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Match report not found")
    return report


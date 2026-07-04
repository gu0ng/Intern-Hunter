from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.graph_job_match import run_job_match_agent, run_job_match_for_saved_job
from app.db import crud
from app.db.database import get_db
from app.schemas.job import JobMatchRequest
from app.schemas.match import MatchReport


router = APIRouter(prefix="/match", tags=["match"])


@router.post("/run", response_model=MatchReport)
def run_match(request: JobMatchRequest):
    try:
        return run_job_match_agent(request.jd_text, persist=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/run", response_model=MatchReport)
def run_match_for_job(job_id: int):
    try:
        return run_job_match_for_saved_job(job_id, persist=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=MatchReport)
def get_match_report(job_id: int, db: Session = Depends(get_db)):
    report = crud.get_latest_match_report(db, job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Match report not found")
    return report

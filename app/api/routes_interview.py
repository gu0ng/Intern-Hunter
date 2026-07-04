from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.graph_interview import run_interview_agent
from app.db import crud
from app.db.database import get_db
from app.schemas.interview import InterviewPrepReport


router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/{job_id}/generate", response_model=InterviewPrepReport)
def generate_interview(job_id: int):
    try:
        return run_interview_agent(job_id, persist=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=list[InterviewPrepReport])
def list_interview_preps(job_id: int, db: Session = Depends(get_db)):
    return crud.list_interview_preps(db, job_id)


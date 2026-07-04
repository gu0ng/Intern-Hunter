from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.schemas.job import JobAnalyzeResult, JobMatchRequest, JobStructured
from app.services.jd_parser import parse_jd
from app.services.job_analyzer import analyze_and_save_job


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    return crud.list_jobs(db)


@router.post("/analyze", response_model=JobAnalyzeResult)
def analyze_job(request: JobMatchRequest, db: Session = Depends(get_db)):
    return analyze_and_save_job(db, request.jd_text)


@router.post("/parse", response_model=JobStructured)
def parse_job(request: JobMatchRequest):
    return parse_jd(request.jd_text)


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job_structured(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

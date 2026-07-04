from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.schemas.job import JobMatchRequest, JobStructured
from app.services.jd_parser import parse_jd


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    return crud.list_jobs(db)


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job_structured(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/parse", response_model=JobStructured)
def parse_job(request: JobMatchRequest):
    return parse_jd(request.jd_text)


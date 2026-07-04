from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db


router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationUpdate(BaseModel):
    status: str | None = None
    next_step: str | None = None
    notes: str | None = None


@router.get("")
def list_applications(db: Session = Depends(get_db)):
    return crud.list_jobs(db)


@router.patch("/{job_id}")
def update_application(job_id: int, request: ApplicationUpdate, db: Session = Depends(get_db)):
    try:
        application = crud.update_application(
            db,
            job_id=job_id,
            status=request.status,
            next_step=request.next_step,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "job_id": application.job_id,
        "status": application.status,
        "next_step": application.next_step,
        "notes": application.notes,
        "updated_at": application.updated_at,
    }


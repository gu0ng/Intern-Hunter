from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.resume import ResumeParseResult, ResumeProfile
from app.services.resume_profiler import load_resume_profile
from app.tools.pdf_resume_tool import PdfExtractionError
from app.tools.resume_parse_tool import parse_resume_pdf_bytes
from app.tools.resume_text_store import load_current_resume_meta, load_current_resume_text, list_saved_resume_texts


router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("/profile", response_model=ResumeProfile)
def get_resume_profile():
    try:
        return load_resume_profile()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/text/current")
def get_current_resume_text():
    try:
        return {"raw_text": load_current_resume_text(), "meta": load_current_resume_meta()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/texts")
def list_resume_texts():
    return list_saved_resume_texts()


@router.post("/parse-pdf", response_model=ResumeParseResult)
async def parse_resume_pdf(file: UploadFile = File(...), save: bool = True):
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        content = await file.read()
        return parse_resume_pdf_bytes(content, save=save, source_filename=file.filename)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

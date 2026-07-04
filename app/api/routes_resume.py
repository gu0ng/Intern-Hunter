from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.resume import ResumeParseResult, ResumeProfile
from app.services.resume_profiler import load_resume_profile, save_resume_profile
from app.tools.pdf_resume_tool import PdfExtractionError
from app.tools.resume_parse_tool import parse_resume_pdf_bytes


router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("/profile", response_model=ResumeProfile)
def get_resume_profile():
    return load_resume_profile()


@router.post("/parse-pdf", response_model=ResumeParseResult)
async def parse_resume_pdf(file: UploadFile = File(...), save: bool = True):
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        content = await file.read()
        return parse_resume_pdf_bytes(content, save=save)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/profile", response_model=ResumeProfile)
def update_resume_profile(profile: ResumeProfile):
    save_resume_profile(profile)
    return profile

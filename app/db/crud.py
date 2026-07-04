import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.schemas.interview import InterviewPrepReport
from app.schemas.job import JobStructured
from app.schemas.match import LLMJudgeReport, MatchReport
from app.tools.hash_utils import compute_jd_hash


APPLICATION_STATUSES = ["未投递", "已投递", "简历筛选中", "笔试", "一面", "二面", "HR 面", "已拒", "已 offer", "放弃"]


def create_job(db: Session, jd_text: str, job: JobStructured, jd_hash: str | None = None) -> models.Job:
    jd_hash = jd_hash or compute_jd_hash(jd_text)
    existing = get_job_by_jd_hash(db, jd_hash)
    if existing:
        _ensure_application(db, existing.id)
        db.commit()
        db.refresh(existing)
        return existing

    db_job = _build_job_model(jd_text, job, jd_hash)
    db.add(db_job)
    db.flush()
    _ensure_application(db, db_job.id)
    db.commit()
    db.refresh(db_job)
    return db_job


def create_job_with_report(db: Session, jd_text: str, job: JobStructured, report: MatchReport, jd_hash: str | None = None) -> MatchReport:
    jd_hash = jd_hash or compute_jd_hash(jd_text)
    existing_report = get_latest_match_report_by_jd_hash(db, jd_hash)
    if existing_report:
        existing_report.llm_notes = _append_note(existing_report.llm_notes, "命中 SQLite 去重，未重复保存岗位。")
        return existing_report

    db_job = get_job_by_jd_hash(db, jd_hash)
    if not db_job:
        db_job = _build_job_model(jd_text, job, jd_hash)
        db.add(db_job)
        db.flush()
    _ensure_application(db, db_job.id)
    return create_match_report_for_job(db, db_job.id, report, jd_hash=jd_hash)


def create_match_report_for_job(db: Session, job_id: int, report: MatchReport, jd_hash: str | None = None) -> MatchReport:
    db_job = get_job(db, job_id)
    if not db_job:
        raise ValueError(f"Job not found: {job_id}")

    score_details = dict(report.score_details)
    score_details["llm_used"] = str(report.llm_used)
    if jd_hash or db_job.jd_hash:
        score_details["jd_hash"] = jd_hash or db_job.jd_hash
    if report.llm_notes:
        score_details["llm_notes"] = report.llm_notes

    persisted_score_details = dict(score_details)
    if report.llm_judge:
        persisted_score_details["llm_judge"] = report.llm_judge.model_dump()

    db_report = models.MatchReport(
        job_id=db_job.id,
        skill_score=report.skill_score,
        project_score=report.project_score,
        constraint_score=report.constraint_score,
        direction_score=report.direction_score,
        preparation_score=report.preparation_score,
        overall_score=report.overall_score,
        strengths=_to_json(report.strengths),
        weaknesses=_to_json(report.weaknesses),
        recommendation=report.recommendation,
        resume_suggestions=_to_json(report.resume_suggestions),
        preparation_suggestions=_to_json(report.preparation_suggestions),
        score_details=_to_json(persisted_score_details),
    )
    db.add(db_report)
    _ensure_application(db, db_job.id)
    db.commit()
    db.refresh(db_job)

    report.job_id = db_job.id
    report.job = _job_to_schema(db_job)
    report.score_details = score_details
    return report

def list_jobs(db: Session) -> list[dict[str, Any]]:
    jobs = db.query(models.Job).order_by(models.Job.created_at.desc()).all()
    rows = []
    for job in jobs:
        latest_report = _latest_report(job)
        rows.append(
            {
                "id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "job_type": job.job_type,
                "category": job.category,
                "overall_score": latest_report.overall_score if latest_report else None,
                "status": job.application.status if job.application else "未投递",
                "next_step": job.application.next_step if job.application else "",
                "notes": job.application.notes if job.application else "",
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
        )
    return rows


def get_job(db: Session, job_id: int) -> models.Job | None:
    return db.query(models.Job).filter(models.Job.id == job_id).first()


def get_job_by_jd_hash(db: Session, jd_hash: str) -> models.Job | None:
    return db.query(models.Job).filter(models.Job.jd_hash == jd_hash).order_by(models.Job.created_at.asc()).first()


def get_job_structured(db: Session, job_id: int) -> JobStructured | None:
    job = get_job(db, job_id)
    if not job:
        return None
    return _job_to_schema(job)


def get_latest_match_report_by_jd_hash(db: Session, jd_hash: str) -> MatchReport | None:
    job = get_job_by_jd_hash(db, jd_hash)
    if not job:
        return None
    return get_latest_match_report(db, job.id)


def get_latest_match_report(db: Session, job_id: int) -> MatchReport | None:
    report = (
        db.query(models.MatchReport)
        .filter(models.MatchReport.job_id == job_id)
        .order_by(models.MatchReport.created_at.desc())
        .first()
    )
    if not report:
        return None
    job = get_job_structured(db, job_id)
    score_details = _from_json(report.score_details, {})
    llm_judge_data = score_details.pop("llm_judge", None)
    llm_judge = LLMJudgeReport.model_validate(llm_judge_data) if isinstance(llm_judge_data, dict) else None
    return MatchReport(
        job_id=job_id,
        job=job,
        skill_score=report.skill_score,
        project_score=report.project_score,
        constraint_score=report.constraint_score,
        direction_score=report.direction_score,
        preparation_score=getattr(report, "preparation_score", 0) or 0,
        overall_score=report.overall_score,
        strengths=_from_json(report.strengths, []),
        weaknesses=_from_json(report.weaknesses, []),
        recommendation=report.recommendation,
        resume_suggestions=_from_json(report.resume_suggestions, []),
        preparation_suggestions=_from_json(report.preparation_suggestions, []),
        score_details=score_details,
        llm_judge=llm_judge,
        llm_used=score_details.get("llm_used") == "True",
        llm_notes=score_details.get("llm_notes", ""),
    )


def update_application(db: Session, job_id: int, status: str | None = None, next_step: str | None = None, notes: str | None = None):
    application = db.query(models.Application).filter(models.Application.job_id == job_id).first()
    if not application:
        application = models.Application(job_id=job_id)
        db.add(application)
    if status:
        if status not in APPLICATION_STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        application.status = status
        if status == "已投递" and application.applied_at is None:
            application.applied_at = datetime.utcnow()
    if next_step is not None:
        application.next_step = next_step
    if notes is not None:
        application.notes = notes
    db.commit()
    db.refresh(application)
    return application


def save_interview_prep(db: Session, report: InterviewPrepReport) -> InterviewPrepReport:
    db_report = models.InterviewPrep(
        job_id=report.job_id,
        technical_questions=_to_json(report.technical_questions),
        project_questions=_to_json(report.project_questions),
        followup_questions=_to_json(report.followup_questions),
        answer_points=_to_json(report.answer_points),
        review_plan=_to_json(report.review_plan),
        self_intro_tip=report.self_intro_tip,
    )
    db.add(db_report)
    db.commit()
    return report


def list_interview_preps(db: Session, job_id: int) -> list[InterviewPrepReport]:
    rows = (
        db.query(models.InterviewPrep)
        .filter(models.InterviewPrep.job_id == job_id)
        .order_by(models.InterviewPrep.created_at.desc())
        .all()
    )
    return [
        InterviewPrepReport(
            job_id=row.job_id,
            technical_questions=_from_json(row.technical_questions, []),
            project_questions=_from_json(row.project_questions, []),
            followup_questions=_from_json(row.followup_questions, []),
            answer_points=_from_json(row.answer_points, []),
            review_plan=_from_json(row.review_plan, []),
            self_intro_tip=row.self_intro_tip,
        )
        for row in rows
    ]


def _build_job_model(jd_text: str, job: JobStructured, jd_hash: str) -> models.Job:
    return models.Job(
        jd_hash=jd_hash,
        company=job.company,
        title=job.title,
        location=job.location,
        job_type=job.job_type,
        category=job.category,
        jd_text=jd_text,
        required_skills=_to_json(job.required_skills),
        bonus_skills=_to_json(job.bonus_skills),
        responsibilities=_to_json(job.responsibilities),
        degree_requirement=job.degree_requirement,
        graduation_requirement=job.graduation_requirement,
        intern_duration=job.intern_duration,
        keywords=_to_json(job.keywords),
        url=job.url,
        risk_notes=job.risk_notes,
        summary=job.summary,
    )


def _ensure_application(db: Session, job_id: int) -> None:
    for item in db.new:
        if isinstance(item, models.Application) and item.job_id == job_id:
            return
    exists = db.query(models.Application).filter(models.Application.job_id == job_id).first()
    if not exists:
        db.add(models.Application(job_id=job_id, status="未投递"))

def _latest_report(job: models.Job) -> models.MatchReport | None:
    if not job.match_reports:
        return None
    return sorted(job.match_reports, key=lambda item: item.created_at, reverse=True)[0]


def _job_to_schema(job: models.Job) -> JobStructured:
    return JobStructured(
        company=job.company,
        title=job.title,
        location=job.location,
        job_type=job.job_type,
        category=job.category,
        responsibilities=_from_json(job.responsibilities, []),
        required_skills=_from_json(job.required_skills, []),
        bonus_skills=_from_json(job.bonus_skills, []),
        degree_requirement=job.degree_requirement,
        graduation_requirement=job.graduation_requirement,
        intern_duration=job.intern_duration,
        keywords=_from_json(job.keywords, []),
        risk_notes=job.risk_notes,
        summary=job.summary,
        url=job.url,
    )


def _append_note(current: str, note: str) -> str:
    return f"{current} {note}".strip() if current else note


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _from_json(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw) if raw else default
    except json.JSONDecodeError:
        return default

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), default="")
    title = Column(String(255), default="")
    location = Column(String(255), default="")
    job_type = Column(String(100), default="")
    category = Column(String(255), default="")
    jd_text = Column(Text, nullable=False)
    required_skills = Column(Text, default="[]")
    bonus_skills = Column(Text, default="[]")
    responsibilities = Column(Text, default="[]")
    degree_requirement = Column(String(255), default="")
    graduation_requirement = Column(String(255), default="")
    intern_duration = Column(String(255), default="")
    keywords = Column(Text, default="[]")
    url = Column(Text, default="")
    risk_notes = Column(Text, default="")
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    match_reports = relationship("MatchReport", back_populates="job", cascade="all, delete-orphan")
    application = relationship("Application", back_populates="job", uselist=False, cascade="all, delete-orphan")
    interview_preps = relationship("InterviewPrep", back_populates="job", cascade="all, delete-orphan")


class MatchReport(Base):
    __tablename__ = "match_reports"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    skill_score = Column(Float, default=0)
    project_score = Column(Float, default=0)
    constraint_score = Column(Float, default=0)
    direction_score = Column(Float, default=0)
    preparation_score = Column(Float, default=0)
    overall_score = Column(Float, default=0)
    strengths = Column(Text, default="[]")
    weaknesses = Column(Text, default="[]")
    recommendation = Column(Text, default="")
    resume_suggestions = Column(Text, default="[]")
    preparation_suggestions = Column(Text, default="[]")
    score_details = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="match_reports")


class InterviewPrep(Base):
    __tablename__ = "interview_preps"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    technical_questions = Column(Text, default="[]")
    project_questions = Column(Text, default="[]")
    followup_questions = Column(Text, default="[]")
    answer_points = Column(Text, default="[]")
    review_plan = Column(Text, default="[]")
    self_intro_tip = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="interview_preps")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    status = Column(String(50), default="未投递")
    applied_at = Column(DateTime, nullable=True)
    next_step = Column(Text, default="")
    notes = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job", back_populates="application")


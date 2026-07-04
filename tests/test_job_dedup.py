from pathlib import Path

from app.agent.graph_job_match import run_job_match_agent
from app.db import models
from app.db.database import SessionLocal, init_db


SAMPLE_RESUME = """
name: 测试用户
education: 本科
major: 网络空间安全
target_roles:
  - AI Agent
skills:
  - Python
  - FastAPI
  - Linux
  - Agent
  - RAG
projects: []
internships: []
research_direction:
  - AI安全
strengths: []
weaknesses: []
city_preference:
  - 北京
availability: 可实习
"""


def test_duplicate_jd_reuses_existing_job(tmp_path: Path):
    init_db()
    resume_path = tmp_path / "resume.yaml"
    resume_path.write_text(SAMPLE_RESUME, encoding="utf-8")
    jd = """
    公司名称：去重测试公司
    岗位名称：AI Agent 应用研发实习生
    工作地点：北京
    任职要求：熟悉 Python、FastAPI、Linux、Agent、RAG。
    """

    first = run_job_match_agent(jd, resume_path=str(resume_path), persist=True)
    second = run_job_match_agent(jd, resume_path=str(resume_path), persist=True)

    assert first.job_id == second.job_id
    with SessionLocal() as db:
        count = db.query(models.Job).filter(models.Job.jd_hash == first.score_details["jd_hash"]).count()
    assert count == 1

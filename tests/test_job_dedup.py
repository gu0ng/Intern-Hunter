from app.db import models
from app.db.database import SessionLocal, init_db
from app.agent.graph_job_match import run_job_match_agent


def test_duplicate_jd_reuses_existing_job():
    init_db()
    jd = """
    公司名称：去重测试公司
    岗位名称：AI Agent 应用研发实习生
    工作地点：北京
    任职要求：熟悉 Python、FastAPI、Linux、Agent、RAG。
    """

    first = run_job_match_agent(jd, persist=True)
    second = run_job_match_agent(jd, persist=True)

    assert first.job_id == second.job_id
    with SessionLocal() as db:
        count = db.query(models.Job).filter(models.Job.jd_hash == first.score_details["jd_hash"]).count()
    assert count == 1

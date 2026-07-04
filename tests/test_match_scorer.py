from app.schemas.job import JobStructured
from app.schemas.resume import ResumeProfile, ResumeProject
from app.services.match_scorer import score_match


def test_score_match_high_for_ai_agent_role():
    profile = ResumeProfile(
        education="本科",
        major="网络空间安全",
        target_roles=["AI Agent", "AI应用研发", "大模型评测"],
        skills=["Python", "FastAPI", "Linux", "Agent", "RAG", "AI安全"],
        projects=[
            ResumeProject(
                name="Intern-Hunter 求职 Agent",
                description="基于 FastAPI 和 LangGraph 的求职 Agent。",
                keywords=["Agent", "RAG", "FastAPI", "AI安全"],
                highlights=["实现 JD 解析、简历画像读取、规则评分和结果入库。"],
            )
        ],
        research_direction=["AI安全", "大模型评测"],
        city_preference=["北京"],
    )
    job = JobStructured(
        company="某智能科技公司",
        title="AI Agent 应用研发实习生",
        location="北京",
        job_type="实习",
        category="AI应用研发 / 大模型",
        required_skills=["Python", "FastAPI", "Linux", "Agent", "RAG"],
        keywords=["大模型", "LLM", "Agent", "RAG", "FastAPI", "AI安全"],
        degree_requirement="本科及以上",
        intern_duration="实习 3 个月以上",
    )

    report = score_match(job, profile)

    assert report.overall_score >= 70
    assert report.skill_score >= 70
    assert report.direction_score >= 75
    assert report.recommendation

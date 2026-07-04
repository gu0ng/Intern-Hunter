from pathlib import Path

from app.services.resume_profiler import collect_resume_keywords, load_resume_profile


SAMPLE_RESUME = """
name: 测试用户
education: 本科
major: 网络空间安全
target_roles:
  - AI Agent
  - 大模型评测
skills:
  - Python
  - FastAPI
  - Agent
projects:
  - name: Intern-Hunter 求职 Agent
    description: 基于 FastAPI 和 LangGraph 的求职 Agent。
    keywords:
      - Agent
      - LangGraph
      - RAG
    highlights:
      - 实现 JD 解析、简历画像读取、规则评分和结果入库。
internships: []
research_direction:
  - AI安全
strengths: []
weaknesses: []
city_preference:
  - 北京
availability: 可实习
"""


def test_load_resume_profile_sample(tmp_path: Path):
    resume_path = tmp_path / "resume.yaml"
    resume_path.write_text(SAMPLE_RESUME, encoding="utf-8")

    profile = load_resume_profile(resume_path)

    assert profile.major == "网络空间安全"
    assert "Python" in profile.skills
    assert profile.projects


def test_collect_resume_keywords_contains_project_keywords(tmp_path: Path):
    resume_path = tmp_path / "resume.yaml"
    resume_path.write_text(SAMPLE_RESUME, encoding="utf-8")
    profile = load_resume_profile(resume_path)
    keywords = collect_resume_keywords(profile)

    assert "AI安全" in keywords
    assert "Agent" in keywords

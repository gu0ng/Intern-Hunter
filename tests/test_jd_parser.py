from app.services.jd_parser import parse_jd_with_rules


def test_parse_jd_extracts_core_fields():
    jd = """
    公司名称：某智能科技公司
    岗位名称：AI Agent 应用研发实习生
    工作地点：北京
    任职要求：
    1. 熟悉 Python、FastAPI、Linux 和数据库。
    2. 了解 LLM、Agent、RAG、Tool Calling。
    加分项：
    1. 有 LangGraph 项目经验。
    """

    parsed = parse_jd_with_rules(jd)

    assert parsed.company == "某智能科技公司"
    assert parsed.title == "AI Agent 应用研发实习生"
    assert parsed.location == "北京"
    assert "Python" in parsed.required_skills
    assert "Agent" in parsed.keywords
    assert parsed.category in {"AI应用研发 / 大模型", "AI安全 / 风控"}

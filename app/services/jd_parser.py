import re

from app.config import settings
from app.schemas.job import JobStructured
from app.tools.deepseek_client import LLMClientError, call_deepseek_json


IMPORTANT_KEYWORDS = [
    "大模型",
    "LLM",
    "Agent",
    "RAG",
    "Tool Calling",
    "AI安全",
    "大模型评测",
    "风险检测",
    "Python",
    "PyTorch",
    "FastAPI",
    "后端",
    "Linux",
    "数据库",
    "SQL",
    "机器学习",
    "深度学习",
    "LangGraph",
    "LangChain",
]

KNOWN_SKILLS = [
    "Python",
    "PyTorch",
    "FastAPI",
    "Linux",
    "SQL",
    "数据库",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "Docker",
    "Kubernetes",
    "机器学习",
    "深度学习",
    "大模型",
    "LLM",
    "Agent",
    "RAG",
    "Tool Calling",
    "LangGraph",
    "LangChain",
    "向量数据库",
    "AI安全",
    "大模型评测",
    "风险检测",
    "数据分析",
    "算法",
]

JD_SYSTEM_PROMPT = """
你是中文实习岗位 JD 解析 Agent。请把用户粘贴的 JD 解析为严格 JSON。
字段必须包括：company, title, location, job_type, category, responsibilities,
required_skills, bonus_skills, degree_requirement, graduation_requirement,
intern_duration, keywords, risk_notes, summary, url。
要求：
1. responsibilities、required_skills、bonus_skills、keywords 必须是字符串数组。
2. 不确定的字段使用 unknown 或空字符串，不要编造。
3. keywords 要覆盖技术方向，例如 LLM、Agent、RAG、AI安全、FastAPI、Linux 等。
4. summary 用中文一句话概括岗位定位。
""".strip()


def parse_jd(jd_text: str) -> JobStructured:
    text = jd_text.strip()
    if not text:
        raise ValueError("JD text cannot be empty.")

    if settings.enable_llm_parsing:
        try:
            return parse_jd_with_deepseek(text)
        except (LLMClientError, KeyError, ValueError):
            pass

    return parse_jd_with_rules(text)


def parse_jd_with_deepseek(text: str) -> JobStructured:
    payload = call_deepseek_json(JD_SYSTEM_PROMPT, "请解析以下 JD，输出 JSON：\n\n" + text[:20000])
    return JobStructured.model_validate(payload)


def parse_jd_with_rules(text: str) -> JobStructured:
    lines = [line.strip(" \t-•*：:") for line in text.splitlines() if line.strip()]
    company = _find_labeled_value(text, ["公司", "公司名称", "企业", "单位"])
    title = _find_labeled_value(text, ["岗位", "职位", "岗位名称", "职位名称"])
    location = _find_labeled_value(text, ["地点", "工作地点", "城市"])
    job_type = _find_labeled_value(text, ["招聘类型", "类型"])
    url = _find_url(text)

    if not title:
        title = _guess_title(lines)
    if not company:
        company = _guess_company(lines)
    if not location:
        location = _guess_location(text)
    if not job_type:
        job_type = "实习" if "实习" in text else "unknown"

    responsibilities = _extract_section_items(text, ["岗位职责", "工作职责", "职责描述", "你将负责"])
    requirements = _extract_section_items(text, ["任职要求", "岗位要求", "职位要求", "我们希望你"])
    bonus_items = _extract_section_items(text, ["加分项", "优先", "加分条件"])

    required_skills = _extract_keywords(" ".join(requirements) + " " + text, KNOWN_SKILLS)
    bonus_skills = _extract_keywords(" ".join(bonus_items), KNOWN_SKILLS)
    keywords = _extract_keywords(text, IMPORTANT_KEYWORDS)

    degree_requirement = _extract_degree(text)
    graduation_requirement = _extract_graduation(text)
    intern_duration = _extract_duration(text)
    category = _infer_category(text, keywords, title)
    risk_notes = _infer_risk_notes(text)
    summary = _build_summary(company, title, location, category, keywords)

    return JobStructured(
        company=company,
        title=title,
        location=location,
        job_type=job_type,
        category=category,
        responsibilities=responsibilities[:8],
        required_skills=required_skills,
        bonus_skills=bonus_skills,
        degree_requirement=degree_requirement,
        graduation_requirement=graduation_requirement,
        intern_duration=intern_duration,
        keywords=keywords,
        risk_notes=risk_notes,
        summary=summary,
        url=url,
    )


def _find_labeled_value(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:：]\s*([^\n\r]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" -；;")
    return ""


def _find_url(text: str) -> str:
    match = re.search(r"https?://[^\s)）]+", text)
    return match.group(0) if match else ""


def _guess_title(lines: list[str]) -> str:
    for line in lines[:8]:
        if any(token in line for token in ["工程师", "实习生", "开发", "算法", "Agent", "评测"]):
            return line[:80]
    return lines[0][:80] if lines else ""


def _guess_company(lines: list[str]) -> str:
    for line in lines[:5]:
        if any(token in line for token in ["公司", "科技", "智能", "集团", "研究院"]):
            return line[:60]
    return ""


def _guess_location(text: str) -> str:
    cities = ["北京", "上海", "深圳", "广州", "杭州", "南京", "成都", "武汉", "远程"]
    found = [city for city in cities if city in text]
    return " / ".join(found[:3]) or "unknown"


def _extract_section_items(text: str, headers: list[str]) -> list[str]:
    all_headers = ["岗位职责", "工作职责", "职责描述", "任职要求", "岗位要求", "职位要求", "加分项", "优先", "工作地点", "薪资"]
    for header in headers:
        match = re.search(rf"{re.escape(header)}\s*[:：]?\s*(.*)", text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        section = match.group(1)
        stop_positions = [
            section.find(next_header)
            for next_header in all_headers
            if next_header not in headers and section.find(next_header) > 0
        ]
        if stop_positions:
            section = section[: min(stop_positions)]
        items = _split_items(section)
        if items:
            return items
    return []


def _split_items(section: str) -> list[str]:
    raw_parts = re.split(r"\n+|[；;]\s*|(?:^|\n)\s*\d+[\.、)]", section)
    items = []
    for part in raw_parts:
        clean = part.strip(" \t\r\n-•*：:")
        if 6 <= len(clean) <= 180 and not _looks_like_header(clean):
            items.append(clean)
    return items


def _looks_like_header(text: str) -> bool:
    return len(text) <= 12 and any(token in text for token in ["要求", "职责", "加分", "地点", "福利"])


def _extract_keywords(text: str, candidates: list[str]) -> list[str]:
    normalized = text.lower()
    result = []
    for keyword in candidates:
        if keyword.lower() in normalized and keyword not in result:
            result.append(keyword)
    return result


def _extract_degree(text: str) -> str:
    if "硕士" in text or "研究生" in text:
        return "硕士及以上"
    if "本科" in text:
        return "本科及以上"
    if "大专" in text:
        return "大专及以上"
    return "unknown"


def _extract_graduation(text: str) -> str:
    match = re.search(r"(20\d{2}\s*[届级年][^，。\n；;]*)", text)
    return match.group(1).strip() if match else "unknown"


def _extract_duration(text: str) -> str:
    patterns = [
        r"每周\s*\d+\s*天[^，。\n；;]*",
        r"\d+\s*个月[^，。\n；;]*",
        r"\d+\s*天\s*/\s*周",
        r"实习\s*\d+\s*个月",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return "unknown"


def _infer_category(text: str, keywords: list[str], title: str) -> str:
    haystack = f"{title} {text}"
    if any(word in haystack for word in ["AI安全", "安全", "风控", "风险检测"]):
        return "AI安全 / 风控"
    if any(word in haystack for word in ["Agent", "RAG", "大模型", "LLM"]):
        return "AI应用研发 / 大模型"
    if any(word in haystack for word in ["后端", "平台", "FastAPI", "数据库"]):
        return "后端平台"
    if keywords:
        return " / ".join(keywords[:2])
    return "未分类"


def _infer_risk_notes(text: str) -> str:
    risks = []
    if any(word in text for word in ["销售", "运营", "用户增长"]):
        risks.append("岗位可能偏运营或业务增长，需要确认技术工作占比。")
    if any(word in text for word in ["可长期", "6个月", "每周5天"]):
        risks.append("实习时长要求较高，需要确认课业时间是否匹配。")
    return " ".join(risks)


def _build_summary(company: str, title: str, location: str, category: str, keywords: list[str]) -> str:
    parts = [part for part in [company, title, location, category] if part]
    if keywords:
        parts.append("关键词：" + "、".join(keywords[:6]))
    return "；".join(parts)

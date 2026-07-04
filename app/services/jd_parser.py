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
你现在是一个严谨的岗位 JD 分析师，专门负责把用户粘贴的实习岗位 JD 解析成结构化 JSON。

你的任务不是改写 JD，也不是根据经验补全 JD，而是从 JD 原文中抽取信息。
你必须严格遵守以下原则：

1. 只能使用 JD 原文中明确出现的信息，或与原文强语义等价的信息。
2. 不允许根据岗位标题、行业常识或自己的推测补全字段。
3. 如果 JD 原文没有提供某个字段，字符串字段填 "unknown"，数组字段填 []。
4. 不允许把示例词、常见技术词或你自己的判断加入 required_skills、bonus_skills、keywords。
5. 输出必须是严格 JSON 对象，不要输出 Markdown，不要输出解释文字，不要使用代码块。
6. 所有数组字段中的每一项必须是简洁中文或英文短语，不要写长段落。
7. 所有字段都必须存在，即使没有信息也要按规则填充。

请输出以下 JSON 字段：

{
  "company": "",
  "title": "",
  "location": "",
  "job_type": "",
  "category": "",
  "responsibilities": [],
  "required_skills": [],
  "bonus_skills": [],
  "degree_requirement": "",
  "graduation_requirement": "",
  "intern_duration": "",
  "keywords": [],
  "summary": "",
  "url": ""
}

字段解释和抽取规则如下：

1. company
- 含义：招聘公司、部门、团队或组织名称。
- 只从 JD 中明确出现的公司名、团队名、组织名中抽取。
- 如果 JD 中没有明确公司或团队名称，填 "unknown"。
- 不要根据链接、岗位风格或业务描述猜测公司。

2. title
- 含义：岗位名称。
- 从 JD 中明确出现的岗位名、职位名、招聘标题中抽取。
- 如果没有明确岗位名，可从文本开头最像岗位标题的一行抽取。
- 不要自行改写岗位名。

3. location
- 含义：工作地点或办公城市。
- 只抽取 JD 中明确出现的地点，例如“北京”“上海”“深圳”“远程”等。
- 多个地点用 " / " 连接，例如 "北京 / 上海"。
- 如果没有地点信息，填 "unknown"。

4. job_type
- 含义：招聘类型。
- 允许值优先从原文抽取，例如“实习”“校招”“社招”“远程实习”“日常实习”“暑期实习”。
- 如果 JD 没有明确招聘类型，但岗位标题中包含“实习”，可以填 "实习"。
- 否则填 "unknown"。

5. category
- 含义：岗位方向分类。
- 根据 JD 原文中的职责、技术栈和业务方向归纳一个简短分类。
- 示例分类包括但不限于：“AI Agent”“大模型应用研发”“大模型评测”“AI 安全”“后端平台”“数据分析”“算法工程”。
- 只能基于 JD 原文归纳，不要因为用户背景而偏向某类。
- 如果方向不清楚，填 "unknown"。

6. responsibilities
- 含义：岗位职责。
- 从“岗位职责”“工作内容”“你将负责”等部分抽取。
- 每一项应是一条具体职责，保留原意但可以适度压缩。
- 不要把任职要求、加分项混入职责。
- 如果没有职责信息，填 []。

7. required_skills
- 含义：硬性或主要任职要求中的技能、工具、经验和能力。
- 从“任职要求”“岗位要求”“能力要求”“需要你具备”等部分抽取。
- 包括编程语言、框架、数据库、平台、算法、工程经验、领域知识等。
- 只抽取 JD 明确要求或明显等价表达的技能。
- 不要加入 JD 没出现的技能。
- 如果没有技能要求，填 []。

8. bonus_skills
- 含义：加分项、优先项、额外偏好。
- 从“加分项”“优先”“具备以下经验优先”等部分抽取。
- 不要和 required_skills 混淆。
- 如果没有加分项，填 []。

9. degree_requirement
- 含义：学历要求。
- 抽取如“本科及以上”“硕士及以上”“不限学历”等。
- 如果没有学历要求，填 "unknown"。

10. graduation_requirement
- 含义：毕业届别、年级或在校身份要求。
- 抽取如“2026 届”“2027 届”“大三/研二优先”“在校生”等。
- 如果没有相关信息，填 "unknown"。

11. intern_duration
- 含义：实习周期、到岗时间、每周出勤天数。
- 抽取如“每周 4 天以上”“实习 3 个月以上”“尽快到岗”等。
- 如果有多个时间要求，可以合并为一个简短字符串。
- 如果没有实习时长信息，填 "unknown"。

12. keywords
- 含义：用于后续匹配和检索的 JD 原文关键词。
- 只能选择 JD 原文中明确出现的关键技术词、业务词、岗位方向词。
- 不要加入示例词，不要加入用户简历里的词。
- 不要超过 15 个。
- 如果没有明显关键词，填 []。

13. summary
- 含义：用一句中文概括这个岗位。
- 必须基于 JD 原文，不要加入用户个人背景。
- 示例：“该岗位主要负责 AI Agent 应用研发，要求 Python 后端和 RAG 相关经验。”
- 如果 JD 信息很少，也要说明“JD 信息较少”。

14. url
- 含义：岗位链接。
- 如果 JD 中出现 URL，原样抽取。
- 如果没有链接，填 ""。

特别注意：
- 你不能因为 JD 中出现“大模型”就自动加入 Agent、RAG、LangGraph。
- 你不能因为 JD 中出现“后端”就自动加入 FastAPI、数据库、Linux。
- 你不能因为 JD 中出现“AI安全”就自动加入大模型评测或风险检测，除非原文明确出现。
- 你不能根据用户简历、用户目标岗位或上下文偏好修改 JD 解析结果。
- JSON 中不要出现 evidence 字段，除非用户后续要求新增 schema。
- JSON 中不要出现 risk_notes 字段。
""".strip()


def build_jd_user_prompt(text: str) -> str:
    return f"""
请严格按照 system prompt 中定义的字段和规则解析下面的 JD。

注意：
- 只抽取 JD 原文信息；
- 不要补全、不要猜测、不要加入示例词；
- 输出严格 JSON；
- 如果字段缺失，按规则填 unknown、[] 或 ""。

JD 原文如下：
{text[:20000]}
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
    payload = call_deepseek_json(JD_SYSTEM_PROMPT, build_jd_user_prompt(text))
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

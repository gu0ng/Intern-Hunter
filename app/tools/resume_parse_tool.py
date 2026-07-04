import re
from typing import Any

from app.schemas.resume import ResumeParseResult, ResumeProfile
from app.tools.deepseek_client import LLMClientError, call_deepseek_json
from app.tools.pdf_resume_tool import extract_pdf_text
from app.tools.resume_text_store import save_resume_text


RESUME_SYSTEM_PROMPT = """
你现在是一名严谨的简历分析师，专门负责解析用户的实习求职简历。

你的任务是：根据用户提供的 PDF 提取文本，抽取简历中的结构化信息，并输出严格 JSON。
输入文本来自 PDF 文本提取工具，可能存在换行混乱、空格缺失、顺序错乱、项目描述被拆行等问题。你需要在不编造信息的前提下进行整理。

核心要求：
1. 只能根据简历原文抽取信息，不允许凭空补全、推测、扩写或加入原文不存在的经历。
2. 如果某个字段在简历中没有明确出现，字符串字段返回空字符串 ""，数组字段返回空数组 []。
3. 所有输出内容优先使用中文。
4. 只输出 JSON，不要输出 Markdown，不要使用 ```json 代码块，不要添加解释说明。
5. JSON 字段名必须严格使用下面定义的字段，不要新增字段，不要遗漏字段。
6. parse_source 必须固定为 "pdf_llm"。
7. internships 字段必须是字符串数组，不允许输出对象数组。
8. projects 字段必须是对象数组，每个项目对象必须包含 name、description、keywords、highlights 四个字段。

字段定义：

- name：
  候选人姓名。只提取简历中明确出现的真实姓名；如果没有明确姓名，返回 ""。

- education：
  教育背景摘要。包括学校、学历、学院、专业、时间等信息。整理为一段简洁中文字符串；不要编造 GPA、排名、奖项。

- major：
  专业名称。只提取明确出现的专业，例如“计算机科学与技术”“软件工程”“自动化”等；没有则返回 ""。

- target_roles：
  求职目标岗位数组。提取简历中明确表达的目标岗位、意向岗位、求职方向，例如“后端开发实习生”“算法实习生”“数据分析实习生”。如果简历没有明确写目标岗位，可以根据项目和技能中高度明确的方向做保守归纳，但不要超过 3 个。

- skills：
  技能数组。提取编程语言、框架、数据库、工具、算法、平台、工程能力等技能关键词，例如 Python、Java、FastAPI、PyTorch、MySQL、Redis、Git、Linux、机器学习。保持为短词条，不要写长句。

- projects：
  项目经历数组。每个项目输出一个对象：
  {
    "name": "项目名称，没有明确名称则用简短概括",
    "description": "项目内容摘要，说明项目目标、本人工作、实现方式、结果",
    "keywords": ["项目相关技术关键词数组"],
    "highlights": ["项目亮点数组，例如性能优化、核心模块、复杂功能、业务成果"]
  }
  只提取简历中明确出现的项目。不要把技能清单伪造成项目。

- internships：
  实习经历数组。每一项必须是一个字符串，概括公司/组织、岗位、时间、工作内容和成果。
  示例：
  ["某公司 后端开发实习生，2025.06-2025.09，负责接口开发、数据库设计和性能优化。"]
  注意：不要输出 {"company": "...", "role": "..."} 这种对象格式。

- research_direction：
  研究方向数组。提取论文、课题、科研项目、实验室经历中明确出现的方向，例如“多模态大模型”“推荐系统”“计算机视觉”。没有科研信息则返回 []。

- strengths：
  优势数组。根据简历原文总结候选人的优势，例如“具备 FastAPI 后端项目经验”“熟悉 Redis 和 MySQL”“有完整项目落地经历”。必须能从简历内容支撑，不要写泛泛的性格评价。

- weaknesses：
  短板数组。根据简历内容保守判断可能缺失的信息，例如“缺少明确实习经历”“缺少线上部署经验”“算法竞赛或论文经历不明显”。不要攻击性表达，不要编造严重缺陷。

- city_preference：
  城市偏好数组。提取简历中明确出现的期望城市、所在地、求职城市。没有明确城市偏好则返回 []。

- availability：
  到岗时间或实习周期。提取类似“每周 4 天”“可实习 3 个月”“2026 年 7 月到岗”等信息。没有明确出现则返回 ""。

- raw_text_summary：
  对简历整体内容的简短摘要，控制在 150 字以内，概括候选人的教育背景、技术方向、项目/实习重点。

- parse_source：
  固定返回 "pdf_llm"。

输出 JSON 示例结构：
{
  "name": "",
  "education": "",
  "major": "",
  "target_roles": [],
  "skills": [],
  "projects": [],
  "internships": [],
  "research_direction": [],
  "strengths": [],
  "weaknesses": [],
  "city_preference": [],
  "availability": "",
  "raw_text_summary": "",
  "parse_source": "pdf_llm"
}
""".strip()


SCALAR_FIELDS = [
    "name",
    "education",
    "major",
    "availability",
    "raw_text_summary",
    "parse_source",
]

STRING_LIST_FIELDS = [
    "target_roles",
    "skills",
    "internships",
    "research_direction",
    "strengths",
    "weaknesses",
    "city_preference",
]


class ResumeParseTool:
    name = "resume_parse_tool"
    description = "Extract PDF text and use DeepSeek to parse it into ResumeProfile."

    def run_pdf(self, pdf_bytes: bytes, save: bool = False) -> ResumeParseResult:
        return parse_resume_pdf_bytes(pdf_bytes, save=save)

    def run_text(self, raw_text: str, save: bool = False) -> ResumeParseResult:
        return parse_resume_text(raw_text, save=save)


def parse_resume_pdf_bytes(pdf_bytes: bytes, save: bool = False, source_filename: str = "resume.pdf") -> ResumeParseResult:
    raw_text = extract_pdf_text(pdf_bytes)
    return parse_resume_text(raw_text, save=save, source_filename=source_filename)


def parse_resume_text(raw_text: str, save: bool = False, source_filename: str = "resume.txt") -> ResumeParseResult:
    try:
        payload = call_deepseek_json(
            RESUME_SYSTEM_PROMPT,
            "请根据下面的 PDF 提取文本解析简历。\n\n"
            "要求：\n"
            "- 严格遵守 system prompt 中的字段定义和输出格式；\n"
            "- 不要编造简历中不存在的信息；\n"
            "- 输出严格 JSON；\n"
            "- 不要输出 Markdown 代码块；\n"
            "- 如果文本中存在 OCR 或 PDF 换行混乱，请在语义上合理合并，但不要新增事实。\n\n"
            "简历 PDF 提取文本如下：\n"
            + raw_text[:20000],
        )
        payload = _normalize_resume_payload(payload)
        profile = ResumeProfile.model_validate(payload)
        result = ResumeParseResult(profile=profile, raw_text=raw_text, saved=False, llm_used=True)
    except (LLMClientError, ValueError, KeyError, TypeError) as exc:
        profile = _fallback_resume_parse(raw_text)
        result = ResumeParseResult(
            profile=profile,
            raw_text=raw_text,
            saved=False,
            llm_used=False,
            fallback_reason=str(exc),
        )

    if save:
        save_resume_text(raw_text, source_filename=source_filename)
        result.saved = True
    return result


def _normalize_resume_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Make model output tolerant before Pydantic validation."""
    if not isinstance(payload, dict):
        raise ValueError("Resume payload must be a JSON object.")

    for field in SCALAR_FIELDS:
        payload[field] = _stringify_scalar(payload.get(field, ""))
    if not payload["parse_source"]:
        payload["parse_source"] = "pdf_llm"

    for field in STRING_LIST_FIELDS:
        payload[field] = _coerce_string_list(payload.get(field))

    payload["projects"] = _coerce_projects(payload.get("projects"))
    return payload


def _coerce_projects(value: Any) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    if isinstance(value, dict):
        value = [value]
    if isinstance(value, str):
        value = _split_text_list(value)

    projects: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return []

    for item in value:
        if item is None or item == "":
            continue
        if isinstance(item, str):
            projects.append({"name": item, "description": "", "keywords": [], "highlights": []})
            continue
        if isinstance(item, dict):
            projects.append(
                {
                    "name": _stringify_scalar(item.get("name") or item.get("project_name") or item.get("title") or ""),
                    "description": _stringify_scalar(item.get("description") or item.get("summary") or item.get("content") or ""),
                    "keywords": _coerce_string_list(item.get("keywords") or item.get("skills") or item.get("tech_stack")),
                    "highlights": _coerce_string_list(item.get("highlights") or item.get("details") or item.get("achievements")),
                }
            )
    return projects


def _coerce_string_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return _split_text_list(value)
    if isinstance(value, dict):
        return [_stringify_mapping(value)]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if item is None or item == "":
                continue
            if isinstance(item, str):
                items.extend(_split_text_list(item))
            elif isinstance(item, dict):
                items.append(_stringify_mapping(item))
            else:
                items.append(str(item).strip())
        return [item for item in items if item]
    return [str(value).strip()] if str(value).strip() else []


def _split_text_list(text: str) -> list[str]:
    normalized = (
        text.replace("\u3001", ",")
        .replace("\uff0c", ",")
        .replace("\uff1b", ";")
        .replace("\u2022", "\n")
    )
    return [item.strip(" -:\t\r") for item in re.split(r"[,;\n]+", normalized) if item.strip(" -:\t\r")]


def _stringify_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return _stringify_mapping(value)
    if isinstance(value, list):
        return "；".join(_stringify_scalar(item) for item in value if _stringify_scalar(item))
    return str(value).strip()


def _stringify_mapping(value: dict[str, Any]) -> str:
    parts = []
    preferred_keys = ["company", "organization", "role", "title", "name", "time", "duration", "description", "content"]
    used = set()
    for key in preferred_keys:
        if key in value and value[key] not in (None, "", []):
            parts.append(_stringify_scalar(value[key]))
            used.add(key)
    for key, item in value.items():
        if key not in used and item not in (None, "", []):
            parts.append(f"{key}: {_stringify_scalar(item)}")
    return "；".join(part for part in parts if part)


def _fallback_resume_parse(raw_text: str) -> ResumeProfile:
    skills = _extract_known_terms(
        raw_text,
        [
            "Python",
            "PyTorch",
            "FastAPI",
            "Linux",
            "SQL",
            "数据库",
            "机器学习",
            "深度学习",
            "大模型",
            "LLM",
            "Agent",
            "RAG",
            "LangGraph",
            "LangChain",
            "AI安全",
            "大模型评测",
            "风险检测",
        ],
    )
    education = "本科" if "本科" in raw_text else "硕士" if "硕士" in raw_text else ""
    major_match = re.search(r"(网络空间安全|计算机科学与技术|软件工程|人工智能|信息安全)", raw_text)
    return ResumeProfile(
        name="",
        education=education,
        major=major_match.group(1) if major_match else "",
        skills=skills,
        target_roles=["AI应用研发", "AI Agent", "大模型评测", "AI安全", "后端平台"],
        research_direction=[term for term in ["AI安全", "大模型评测", "风险检测"] if term in raw_text],
        strengths=["已通过本地规则从简历文本中提取部分技能关键词。"],
        weaknesses=["DeepSeek 简历解析未成功，当前结果为规则降级版本，需要人工复核。"],
        raw_text_summary=raw_text[:500],
        parse_source="pdf_rule_fallback",
    )


def _extract_known_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]

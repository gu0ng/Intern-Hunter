import re
from typing import Any

import yaml

from app.config import settings
from app.schemas.resume import ResumeParseResult, ResumeProfile
from app.tools.deepseek_client import LLMClientError, call_deepseek_json
from app.tools.pdf_resume_tool import extract_pdf_text


RESUME_SYSTEM_PROMPT = """
You are a technical resume parsing agent for Chinese internship candidates.
Parse the PDF-extracted resume text into strict JSON.
Required fields: name, education, major, target_roles, skills, projects, internships,
research_direction, strengths, weaknesses, city_preference, availability,
raw_text_summary, parse_source.
Rules:
1. Return Chinese content when possible.
2. projects must be an array of objects. Each object has name, description, keywords, highlights.
3. target_roles, skills, internships, research_direction, strengths, weaknesses, city_preference must be arrays of strings.
4. If a field is unknown, use an empty string for scalar fields and an empty array for array fields.
5. parse_source must be pdf_llm.
Return JSON only.
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


def parse_resume_pdf_bytes(pdf_bytes: bytes, save: bool = False) -> ResumeParseResult:
    raw_text = extract_pdf_text(pdf_bytes)
    return parse_resume_text(raw_text, save=save)


def parse_resume_text(raw_text: str, save: bool = False) -> ResumeParseResult:
    try:
        payload = call_deepseek_json(
            RESUME_SYSTEM_PROMPT,
            "Parse this resume text into the required JSON schema:\n\n" + raw_text[:20000],
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
        save_resume_profile(result.profile)
        result.saved = True
    return result


def save_resume_profile(profile: ResumeProfile) -> None:
    path = settings.resolve_path(settings.resume_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(profile.model_dump(), file, allow_unicode=True, sort_keys=False)


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

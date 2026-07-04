import re

import yaml

from app.config import settings
from app.schemas.resume import ResumeParseResult, ResumeProfile
from app.tools.deepseek_client import LLMClientError, call_deepseek_json
from app.tools.pdf_resume_tool import extract_pdf_text


RESUME_SYSTEM_PROMPT = """
你是中文技术简历解析 Agent。请从用户提供的 PDF 简历文本中抽取结构化简历画像。
只输出严格 JSON，字段必须包括：
name, education, major, target_roles, skills, projects, internships,
research_direction, strengths, weaknesses, city_preference, availability, raw_text_summary, parse_source。
projects 必须是对象数组，每个对象包含 name, description, keywords, highlights。
如果字段无法确定，字符串用空字符串，数组用空数组。parse_source 固定为 pdf_llm。
""".strip()


def parse_resume_pdf_bytes(pdf_bytes: bytes, save: bool = False) -> ResumeParseResult:
    raw_text = extract_pdf_text(pdf_bytes)
    return parse_resume_text(raw_text, save=save)


def parse_resume_text(raw_text: str, save: bool = False) -> ResumeParseResult:
    try:
        payload = call_deepseek_json(
            RESUME_SYSTEM_PROMPT,
            "请解析以下简历文本，输出 JSON：\n\n" + raw_text[:20000],
        )
        profile = ResumeProfile.model_validate(payload)
        result = ResumeParseResult(profile=profile, raw_text=raw_text, saved=False, llm_used=True)
    except (LLMClientError, ValueError, KeyError) as exc:
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

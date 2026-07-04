from app.schemas.job import JobStructured
from app.schemas.match import MatchReport
from app.schemas.resume import ResumeProfile
from app.tools.deepseek_client import LLMClientError, call_deepseek_json


MATCH_ADVICE_SYSTEM_PROMPT = """
你是实习求职匹配报告 Agent。你会收到：结构化 JD、简历画像、规则评分报告。
请基于规则评分做补充分析，不要推翻明确的规则分数。
只输出严格 JSON，字段必须包括：
strengths, weaknesses, recommendation, resume_suggestions, preparation_suggestions, llm_notes。
所有列表字段必须是字符串数组。建议要具体，避免“提升能力”这类空话。
""".strip()


def enrich_match_report_with_deepseek(job: JobStructured, profile: ResumeProfile, report: MatchReport) -> MatchReport:
    prompt = {
        "job": job.model_dump(),
        "resume": profile.model_dump(),
        "rule_report": report.model_dump(),
    }
    try:
        payload = call_deepseek_json(MATCH_ADVICE_SYSTEM_PROMPT, str(prompt))
    except LLMClientError as exc:
        report.llm_used = False
        report.llm_notes = f"DeepSeek 建议生成未启用或调用失败，当前报告为规则版本：{exc}"
        return report

    report.strengths = _pick_list(payload.get("strengths"), report.strengths)
    report.weaknesses = _pick_list(payload.get("weaknesses"), report.weaknesses)
    report.recommendation = str(payload.get("recommendation") or report.recommendation)
    report.resume_suggestions = _pick_list(payload.get("resume_suggestions"), report.resume_suggestions)
    report.preparation_suggestions = _pick_list(payload.get("preparation_suggestions"), report.preparation_suggestions)
    report.llm_used = True
    report.llm_notes = str(payload.get("llm_notes") or "DeepSeek 已基于规则评分补充中文建议。")
    return report


def _pick_list(value, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if cleaned:
            return cleaned
    return fallback

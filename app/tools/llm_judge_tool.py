from typing import Any

from app.schemas.job import JobStructured
from app.schemas.match import LLMJudgeReport, MatchReport
from app.schemas.resume import ResumeProfile
from app.tools.deepseek_client import LLMClientError, call_deepseek_json


LLM_JUDGE_SYSTEM_PROMPT = """
你现在是一名严谨的实习岗位匹配度评估官，也是一名 LLM Judge。
你的任务是：基于候选人的结构化简历画像和结构化岗位 JD，直接判断候选人与岗位的适配程度，并输出严格 JSON 格式的匹配度报告。

你会收到两个核心输入：
1. resume_profile：候选人的结构化简历画像，包括教育背景、专业、目标岗位、技能、项目、实习、研究方向、优势、短板、城市偏好、可实习时间等。
2. job：结构化岗位 JD，包括公司、岗位名称、地点、岗位类型、岗位类别、职责、必备技能、加分技能、学历要求、毕业时间要求、实习周期、关键词、岗位摘要、URL 等。

评估原则：
1. 只能根据输入中的 resume_profile 和 job 进行判断，不允许编造候选人没有的经历、技能、项目或成果。
2. 不要因为候选人表达积极或岗位看起来热门就提高分数，必须基于证据评分。
3. 不要只做关键词匹配，要结合技能深度、项目相关性、岗位职责、硬性条件、准备成本和发展价值综合判断。
4. 如果 JD 信息不足，要明确说明不确定性，并适当降低置信度。
5. 如果简历信息不足，要指出缺失信息，不要自动假设候选人具备能力。
6. 输出必须是严格 JSON，不要输出 Markdown，不要使用 ```json 代码块，不要添加额外解释。
7. 所有数组字段必须是字符串数组。
8. 所有分数字段必须是 0 到 100 的数字，分数越高表示匹配度越高。
9. overall_score 不应简单平均，应综合岗位硬性要求、核心能力匹配、项目证明强度和短期准备成本给出。
10. 评价要面向“是否值得投递”和“如何提高通过率”，不要写空泛建议。

评分尺度：
- 90-100：高度匹配。候选人的核心技能、项目经历、岗位方向和硬性条件都明显匹配，可以优先投递。
- 80-89：较高匹配。主要要求基本覆盖，存在少量可通过简历表达或短期准备弥补的问题。
- 65-79：中等匹配。方向相关，但存在明显技能、项目或硬性条件缺口，适合有针对性修改简历后投递。
- 50-64：偏低匹配。部分方向相关，但核心要求覆盖不足，投递成功率不高。
- 0-49：低匹配。岗位方向、技能要求或硬性条件与候选人差距较大，不建议优先投递。

字段定义：

- overall_score：
  总体匹配度分数，0-100。综合判断候选人与岗位的真实适配程度。

- decision：
  投递决策，只能从以下枚举中选择一个：
  ["强烈推荐投递", "建议投递", "可尝试投递", "谨慎投递", "暂不建议投递"]

- confidence：
  判断置信度，只能从以下枚举中选择一个：
  ["high", "medium", "low"]
  如果 JD 或简历信息不足，置信度应为 medium 或 low。

- dimension_scores：
  分维度评分对象，必须包含以下字段：
  {
    "skill_match": 0,
    "project_relevance": 0,
    "role_direction": 0,
    "hard_constraints": 0,
    "experience_depth": 0,
    "preparation_cost": 0
  }

  skill_match：候选人技能与 JD 必备技能、加分技能的匹配程度。
  project_relevance：候选人项目经历与岗位职责、业务场景、技术栈的相关程度。
  role_direction：候选人目标岗位、研究方向、项目方向与岗位方向的一致性。
  hard_constraints：学历、毕业时间、地点、实习周期、到岗时间等硬性条件匹配程度。
  experience_depth：候选人经历是否能证明“做过、做深、能讲清楚”，而不只是列出关键词。
  preparation_cost：候选人短期补齐岗位缺口的难度。准备成本越低，分数越高。

- matched_evidence：
  候选人与岗位匹配的证据数组。每条必须说明“岗位要求”和“简历证据”的对应关系。
  示例："JD 要求 FastAPI 接口开发，简历项目中包含 FastAPI 后端服务实现。"

- gap_evidence：
  候选人与岗位之间的缺口数组。每条必须说明缺口来自 JD 的哪类要求。
  示例："JD 强调 Redis 缓存经验，但简历画像中没有明确 Redis 项目实践。"

- risk_notes：
  风险提示数组。只写真实影响投递成功率的风险，例如学历不符、实习时长不满足、项目深度不足、岗位方向偏离等。
  如果没有明显风险，返回 []。

- recommendation：
  一段完整中文结论，说明是否建议投递、理由、优先级和需要注意的问题。不要超过 180 字。

- resume_suggestions：
  简历修改建议数组。必须具体到可以修改的内容，例如补充哪个项目、突出哪个技能、把哪类经历前置。
  不要写“提升项目能力”“加强技术学习”这类空话。

- preparation_suggestions：
  面试和投递准备建议数组。必须结合 JD 给出，例如准备哪些项目讲解、哪些技术问题、哪些业务场景。

- missing_keywords：
  JD 中重要但简历画像未明确覆盖的关键词数组。只列确实重要的关键词。

- highlight_keywords：
  简历中应在投递该岗位时重点突出的关键词数组。

- interview_focus：
  面试中最可能被追问的方向数组，例如项目架构、技术选型、指标结果、实习稳定性、岗位理解等。

- llm_notes：
  简短说明本次判断依据，例如“本报告基于结构化简历画像和结构化 JD 直接评估，未使用外部信息。”

输出 JSON 示例结构：
{
  "overall_score": 0,
  "decision": "",
  "confidence": "",
  "dimension_scores": {
    "skill_match": 0,
    "project_relevance": 0,
    "role_direction": 0,
    "hard_constraints": 0,
    "experience_depth": 0,
    "preparation_cost": 0
  },
  "matched_evidence": [],
  "gap_evidence": [],
  "risk_notes": [],
  "recommendation": "",
  "resume_suggestions": [],
  "preparation_suggestions": [],
  "missing_keywords": [],
  "highlight_keywords": [],
  "interview_focus": [],
  "llm_notes": ""
}
""".strip()


LIST_FIELDS = [
    "matched_evidence",
    "gap_evidence",
    "risk_notes",
    "resume_suggestions",
    "preparation_suggestions",
    "missing_keywords",
    "highlight_keywords",
    "interview_focus",
]

DIMENSION_FIELDS = [
    "skill_match",
    "project_relevance",
    "role_direction",
    "hard_constraints",
    "experience_depth",
    "preparation_cost",
]


def attach_llm_judge(job: JobStructured, profile: ResumeProfile, report: MatchReport) -> MatchReport:
    user_prompt = {
        "resume_profile": profile.model_dump(),
        "job": job.model_dump(),
        "rule_report_for_reference": report.model_dump(exclude={"llm_judge"}),
    }
    try:
        payload = call_deepseek_json(LLM_JUDGE_SYSTEM_PROMPT, str(user_prompt))
        judge = LLMJudgeReport.model_validate(_normalize_judge_payload(payload))
    except (LLMClientError, ValueError, KeyError, TypeError) as exc:
        report.llm_used = False
        report.llm_notes = f"DeepSeek LLM Judge 未启用或调用失败：{exc}"
        report.llm_judge = None
        return report

    report.llm_judge = judge
    report.llm_used = True
    report.llm_notes = judge.llm_notes or "DeepSeek LLM Judge 已基于结构化简历和 JD 直接评估。"
    return report


def _normalize_judge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LLM judge payload must be a JSON object.")

    payload["overall_score"] = _score(payload.get("overall_score"))
    payload["decision"] = str(payload.get("decision") or "").strip()
    payload["confidence"] = str(payload.get("confidence") or "").strip()
    payload["recommendation"] = str(payload.get("recommendation") or "").strip()
    payload["llm_notes"] = str(payload.get("llm_notes") or "").strip()

    dimensions = payload.get("dimension_scores")
    if not isinstance(dimensions, dict):
        dimensions = {}
    payload["dimension_scores"] = {field: _score(dimensions.get(field)) for field in DIMENSION_FIELDS}

    for field in LIST_FIELDS:
        payload[field] = _string_list(payload.get(field))
    return payload


def _score(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(0.0, min(100.0, number))


def _string_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []
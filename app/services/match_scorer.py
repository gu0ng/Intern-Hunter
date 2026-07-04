from app.schemas.job import JobStructured
from app.schemas.match import MatchReport
from app.schemas.resume import ResumeProfile
from app.services.resume_profiler import collect_resume_keywords
from app.services.resume_suggester import build_resume_suggestions


HIGH_MATCH_DIRECTIONS = [
    "大模型评测",
    "AI安全",
    "AI Agent",
    "Agent",
    "AI应用研发",
    "后端平台",
    "大模型训练",
    "推理平台",
    "安全研发",
    "风控AI",
]

LOW_MATCH_DIRECTIONS = ["纯运营", "纯销售", "纯视觉生成", "纯语音算法", "泛产品", "用户研究"]

PROJECT_FOCUS_KEYWORDS = [
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
]


def score_match(job: JobStructured, profile: ResumeProfile) -> MatchReport:
    resume_keywords = collect_resume_keywords(profile)
    normalized_resume = _normalize_set(resume_keywords)

    skill_score, matched_skills, missing_skills = _score_skills(job, normalized_resume)
    project_score, matched_project_keywords = _score_projects(job, normalized_resume)
    direction_score, direction_reason = _score_direction(job, profile)
    constraint_score, constraint_reason = _score_constraints(job, profile)
    preparation_score, preparation_reason = _score_preparation(job, missing_skills)

    overall = (
        0.30 * skill_score
        + 0.30 * project_score
        + 0.20 * direction_score
        + 0.10 * constraint_score
        + 0.10 * preparation_score
    )

    strengths = _build_strengths(job, matched_skills, matched_project_keywords, direction_score)
    weaknesses = _build_weaknesses(missing_skills, constraint_reason, preparation_reason)
    recommendation = _build_recommendation(overall, job, weaknesses)
    resume_suggestions = build_resume_suggestions(job, profile, missing_skills)
    preparation_suggestions = _build_preparation_suggestions(job, missing_skills)

    return MatchReport(
        job=job,
        skill_score=round(skill_score, 1),
        project_score=round(project_score, 1),
        constraint_score=round(constraint_score, 1),
        direction_score=round(direction_score, 1),
        preparation_score=round(preparation_score, 1),
        overall_score=round(overall, 1),
        strengths=strengths,
        weaknesses=weaknesses,
        recommendation=recommendation,
        resume_suggestions=resume_suggestions,
        preparation_suggestions=preparation_suggestions,
        score_details={
            "skill": f"命中技能：{_join_or_unknown(matched_skills)}；缺口：{_join_or_unknown(missing_skills)}",
            "project": f"项目关键词命中：{_join_or_unknown(matched_project_keywords)}",
            "direction": direction_reason,
            "constraint": constraint_reason,
            "preparation": preparation_reason,
        },
    )


def _score_skills(job: JobStructured, normalized_resume: set[str]) -> tuple[float, list[str], list[str]]:
    required = job.required_skills or job.keywords
    if not required:
        return 65.0, [], []
    matched = [skill for skill in required if skill.lower() in normalized_resume]
    missing = [skill for skill in required if skill.lower() not in normalized_resume]
    base = 35
    score = base + 65 * len(matched) / max(len(required), 1)
    return min(score, 100.0), matched, missing


def _score_projects(job: JobStructured, normalized_resume: set[str]) -> tuple[float, list[str]]:
    job_keywords = [keyword for keyword in PROJECT_FOCUS_KEYWORDS if keyword in job.keywords or keyword in job.required_skills]
    if not job_keywords:
        job_keywords = job.keywords[:]
    if not job_keywords:
        return 60.0, []
    matched = [keyword for keyword in job_keywords if keyword.lower() in normalized_resume]
    score = 30 + 70 * len(matched) / max(len(job_keywords), 1)
    return min(score, 100.0), matched


def _score_direction(job: JobStructured, profile: ResumeProfile) -> tuple[float, str]:
    text = _job_text(job)
    if any(direction in text for direction in LOW_MATCH_DIRECTIONS):
        return 35.0, "岗位文本包含低匹配方向，需要确认是否偏非技术。"
    high_hits = [direction for direction in HIGH_MATCH_DIRECTIONS if direction in text]
    profile_hits = [role for role in profile.target_roles + profile.research_direction if role and role in text]
    hits = list(dict.fromkeys(high_hits + profile_hits))
    if hits:
        return min(100.0, 70 + 5 * len(hits)), "方向命中：" + "、".join(hits[:6])
    return 55.0, "未明显命中目标方向，建议人工确认岗位技术方向。"


def _score_constraints(job: JobStructured, profile: ResumeProfile) -> tuple[float, str]:
    score = 75.0
    notes = []
    if job.degree_requirement == "unknown":
        notes.append("学历要求 unknown，未扣重分。")
    elif "本科" in job.degree_requirement and "本科" in profile.education:
        score += 10
        notes.append("学历要求与本科背景匹配。")
    elif "硕士" in job.degree_requirement and "本科" in profile.education:
        score -= 25
        notes.append("岗位偏硕士及以上，本科背景可能有约束。")

    if job.location == "unknown" or not job.location:
        notes.append("地点 unknown，未扣重分。")
    elif profile.city_preference and any(city in job.location for city in profile.city_preference):
        score += 10
        notes.append("城市符合偏好。")

    if job.intern_duration == "unknown":
        notes.append("实习时长 unknown，未扣重分。")
    elif any(token in job.intern_duration for token in ["6个月", "每周5天", "5天"]):
        score -= 10
        notes.append("实习时长要求较高，需要确认时间安排。")

    return max(0.0, min(score, 100.0)), " ".join(notes) or "未发现明显硬性约束。"


def _score_preparation(job: JobStructured, missing_skills: list[str]) -> tuple[float, str]:
    if not missing_skills:
        return 85.0, "核心技能缺口较少，准备成本可控。"
    agent_gap = any(skill in missing_skills for skill in ["Agent", "RAG", "Tool Calling", "LangGraph", "LangChain"])
    if agent_gap and any(keyword in job.keywords for keyword in ["Agent", "RAG", "大模型", "LLM"]):
        return 62.0, "主要缺口是 Agent/RAG 工程项目，但岗位方向高度相关，适合通过本项目补齐。"
    if len(missing_skills) >= 5:
        return 45.0, "缺口技能较多，短期准备成本较高。"
    return 68.0, "存在少量技能缺口，需要针对 JD 补充项目表达和面试准备。"


def _build_strengths(job: JobStructured, matched_skills: list[str], matched_project_keywords: list[str], direction_score: float) -> list[str]:
    strengths = []
    if matched_skills:
        strengths.append("技能栈命中岗位要求：" + "、".join(matched_skills[:6]) + "。")
    if matched_project_keywords:
        strengths.append("项目关键词与岗位相关：" + "、".join(matched_project_keywords[:6]) + "。")
    if direction_score >= 75:
        strengths.append("岗位方向与 AI 应用研发、AI 安全或大模型评测目标方向较一致。")
    if job.category:
        strengths.append(f"岗位类别为“{job.category}”，适合作为简历项目展示场景。")
    return strengths or ["当前 JD 信息较少，暂未识别出明确优势，建议补充完整岗位要求后重新分析。"]


def _build_weaknesses(missing_skills: list[str], constraint_reason: str, preparation_reason: str) -> list[str]:
    weaknesses = []
    if missing_skills:
        weaknesses.append("JD 中出现但简历画像未明确覆盖的技能：" + "、".join(missing_skills[:6]) + "。")
    if "约束" in constraint_reason or "较高" in constraint_reason or "硕士" in constraint_reason:
        weaknesses.append(constraint_reason)
    if "缺口" in preparation_reason:
        weaknesses.append(preparation_reason)
    return weaknesses or ["暂无明显短板，但仍建议按岗位关键词微调项目描述。"]


def _build_recommendation(overall: float, job: JobStructured, weaknesses: list[str]) -> str:
    job_name = job.title or "该岗位"
    if overall >= 80:
        return f"推荐优先投递 {job_name}。匹配度较高，建议重点强化项目量化结果和岗位关键词。"
    if overall >= 65:
        return f"可以投递 {job_name}，但需要在简历和面试准备中补齐短板：{weaknesses[0]}"
    if overall >= 50:
        return f"谨慎投递 {job_name}。方向可能相关，但当前技能或项目表达缺口较明显，建议准备后再投。"
    return f"暂不建议优先投递 {job_name}。当前匹配度较低，除非该岗位有强烈发展价值或内推机会。"


def _build_preparation_suggestions(job: JobStructured, missing_skills: list[str]) -> list[str]:
    suggestions = []
    if missing_skills:
        suggestions.append("围绕缺口技能准备 3-5 个可讲清楚的实践例子：" + "、".join(missing_skills[:5]) + "。")
    if any(keyword in job.keywords for keyword in ["大模型", "LLM", "Agent", "RAG"]):
        suggestions.append("准备一个 Agent/RAG 项目讲解：需求、工作流节点、工具调用、数据库保存、失败处理和部署方式。")
    if any(keyword in job.keywords for keyword in ["AI安全", "风险检测", "大模型评测"]):
        suggestions.append("准备 AI 安全评测常见问题：风险类型、数据构造、评测指标、误报漏报分析和防护策略。")
    suggestions.append("把 JD 中的职责逐条映射到简历项目，避免面试时只泛泛介绍技术栈。")
    return suggestions[:5]


def _normalize_set(values: set[str]) -> set[str]:
    normalized = set()
    for value in values:
        normalized.add(value.lower())
        normalized.add(value.replace(" ", "").lower())
    return normalized


def _job_text(job: JobStructured) -> str:
    return " ".join(
        [
            job.title,
            job.category,
            job.summary,
            " ".join(job.keywords),
            " ".join(job.required_skills),
            " ".join(job.responsibilities),
        ]
    )


def _join_or_unknown(values: list[str]) -> str:
    return "、".join(values) if values else "无明确命中"


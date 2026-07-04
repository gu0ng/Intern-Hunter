from app.schemas.job import JobStructured
from app.schemas.resume import ResumeProfile


def build_resume_suggestions(job: JobStructured, profile: ResumeProfile, missing_skills: list[str]) -> list[str]:
    suggestions: list[str] = []
    if missing_skills:
        suggestions.append(
            "在技能栈中补充或突出与岗位直接相关的能力："
            + "、".join(missing_skills[:5])
            + "。如果只是学习中，不要写成熟练，建议写成“了解/实践过”。"
        )
    if any(keyword in job.keywords for keyword in ["Agent", "RAG", "Tool Calling", "LangGraph"]):
        suggestions.append(
            "该岗位强调 Agent 工程经验，建议在项目经历中突出 FastAPI + LangGraph 工作流、工具调用、RAG 检索和结果入库能力。"
        )
    if any(keyword in job.keywords for keyword in ["AI安全", "大模型评测", "风险检测"]):
        suggestions.append(
            "岗位方向与 AI 安全/评测相关，建议把大模型训练数据异常识别、输入侧风险检测、评测指标和误报分析写成可量化成果。"
        )
    if not profile.internships:
        suggestions.append("如果缺少正式实习经历，建议把课程设计和项目按工程项目格式呈现：背景、方案、技术栈、指标、复盘。")
    return suggestions[:5]


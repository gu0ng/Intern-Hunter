from app.schemas.interview import InterviewPrepReport
from app.schemas.job import JobStructured
from app.schemas.resume import ResumeProfile


def generate_interview_prep(job_id: int, job: JobStructured, profile: ResumeProfile) -> InterviewPrepReport:
    keywords = job.keywords or job.required_skills or ["项目工程化", "后端服务", "模型评测"]
    technical_questions = [
        f"请解释你如何在项目中使用 {keyword}，遇到的核心问题是什么？" for keyword in keywords[:5]
    ]
    project_questions = [
        "你的大模型训练数据异常识别项目如何定义异常样本？指标如何设计？",
        "输入侧风险检测项目如何降低误报和漏报？",
        "如果把当前求职 Agent 项目扩展为 RAG 系统，你会如何设计数据流和检索策略？",
    ]
    followup_questions = [
        "如果线上接口超时或 LLM 返回非 JSON，你如何降级？",
        "如何证明你的匹配评分不是纯主观判断？",
        "如何设计数据库表来支持多岗位、多轮面试和复盘？",
    ]
    answer_points = [
        "回答时按背景、任务、方案、结果、复盘组织，不要只罗列技术名词。",
        "强调规则评分、结构化输出、异常处理、数据落库和可复现测试。",
        "结合岗位 JD，把自己的 AI 安全和大模型评测经历映射到业务问题。",
    ]
    review_plan = [
        "第 1 天：复盘 JD 技能点，补齐 Agent/RAG/Tool Calling 基础概念和项目讲解稿。",
        "第 2 天：准备 AI 安全、风险检测、大模型评测相关问题和指标设计。",
        "第 3 天：模拟面试，重点练习项目深挖、失败案例、工程化取舍和反问问题。",
    ]
    return InterviewPrepReport(
        job_id=job_id,
        technical_questions=technical_questions,
        project_questions=project_questions,
        followup_questions=followup_questions,
        answer_points=answer_points,
        review_plan=review_plan,
        self_intro_tip=f"自我介绍中先对齐 {job.title or '目标岗位'}，再突出网络空间安全背景、AI 安全评测项目和 Agent 工程补齐计划。",
    )


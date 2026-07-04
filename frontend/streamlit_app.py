from pathlib import Path
import os

import requests
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="Intern-Hunter", layout="wide")


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, json=None, files=None, params=None, timeout=120):
    response = requests.post(f"{API_BASE_URL}{path}", json=json, files=files, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_patch(path: str, json=None):
    response = requests.patch(f"{API_BASE_URL}{path}", json=json, timeout=30)
    response.raise_for_status()
    return response.json()


def render_api_error(exc: Exception):
    st.error(f"API 调用失败：{exc}")
    st.caption("请确认 FastAPI 已启动：uvicorn app.main:app --reload")


st.sidebar.title("Intern-Hunter")
st.sidebar.caption(f"API: {API_BASE_URL}")
page = st.sidebar.radio("页面", ["简历解析", "岗位分析", "匹配度报告", "面试准备", "投递看板"])

if page == "简历解析":
    st.title("简历 PDF 解析")
    st.write("上传 PDF 后，系统会先抽取文本，再调用 DeepSeek 将简历解析为结构化 ResumeProfile。")
    uploaded = st.file_uploader("上传简历 PDF", type=["pdf"])
    save_profile = st.checkbox("解析后保存为当前简历画像 data/resume/resume.yaml", value=True)
    if st.button("解析简历", type="primary"):
        if uploaded is None:
            st.warning("请先上传 PDF 文件。")
        else:
            try:
                with st.spinner("正在解析 PDF 并调用 DeepSeek..."):
                    result = api_post(
                        "/resume/parse-pdf",
                        files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                        params={"save": str(save_profile).lower()},
                        timeout=180,
                    )
                st.success("简历解析完成。" if result.get("llm_used") else "简历已用规则降级解析，请检查 DeepSeek 配置。")
                if result.get("fallback_reason"):
                    st.warning(result["fallback_reason"])
                st.subheader("结构化简历画像")
                st.json(result.get("profile", {}))
                with st.expander("PDF 抽取文本"):
                    st.text(result.get("raw_text", "")[:8000])
            except Exception as exc:
                render_api_error(exc)

elif page == "岗位分析":
    st.title("岗位分析")
    sample_text = ""
    sample_path = PROJECT_ROOT / "data" / "examples" / "sample_jd.txt"
    if sample_path.exists():
        sample_text = sample_path.read_text(encoding="utf-8")
    jd_text = st.text_area("粘贴岗位 JD", value=sample_text, height=360)
    if st.button("分析岗位", type="primary"):
        if not jd_text.strip():
            st.warning("请先粘贴 JD。")
        else:
            try:
                with st.spinner("正在调用 Agent：检查 Redis/SQLite 缓存 -> 未命中时解析 JD、评分、生成建议并保存..."):
                    report = api_post("/match/run", json={"jd_text": jd_text}, timeout=180)
                cache_hit = report.get("score_details", {}).get("cache_hit", "")
                if cache_hit in {"redis_precheck", "sqlite_precheck", "redis", "sqlite"}:
                    st.success(f"命中已有岗位，job_id={report.get('job_id')}，未重复保存")
                else:
                    st.success(f"已保存岗位，job_id={report.get('job_id')}")
                st.subheader("结构化岗位")
                st.json(report.get("job", {}))
                st.subheader("匹配结论")
                st.metric("总体匹配度", report.get("overall_score"))
                st.write(report.get("recommendation"))
                st.caption(report.get("llm_notes", ""))
            except Exception as exc:
                render_api_error(exc)

elif page == "匹配度报告":
    st.title("匹配度报告")
    try:
        jobs = api_get("/jobs")
    except Exception as exc:
        render_api_error(exc)
        jobs = []
    if not jobs:
        st.info("还没有保存的岗位，请先在“岗位分析”页面分析一个 JD。")
    else:
        selected = st.selectbox(
            "选择岗位",
            jobs,
            format_func=lambda row: f"{row['id']} | {row['company'] or '未知公司'} | {row['title'] or '未知岗位'}",
        )
        try:
            report = api_get(f"/match/{selected['id']}")
            cols = st.columns(5)
            cols[0].metric("总体", report.get("overall_score"))
            cols[1].metric("技能", report.get("skill_score"))
            cols[2].metric("项目", report.get("project_score"))
            cols[3].metric("方向", report.get("direction_score"))
            cols[4].metric("约束", report.get("constraint_score"))
            st.subheader("投递建议")
            st.write(report.get("recommendation"))
            st.caption(report.get("llm_notes", ""))
            st.subheader("优势")
            for item in report.get("strengths", []):
                st.write(f"- {item}")
            st.subheader("短板")
            for item in report.get("weaknesses", []):
                st.write(f"- {item}")
            st.subheader("简历修改建议")
            for item in report.get("resume_suggestions", []):
                st.write(f"- {item}")
            st.subheader("准备建议")
            for item in report.get("preparation_suggestions", []):
                st.write(f"- {item}")
            st.subheader("评分依据")
            st.json(report.get("score_details", {}))
        except Exception as exc:
            render_api_error(exc)

elif page == "面试准备":
    st.title("面试准备")
    try:
        jobs = api_get("/jobs")
    except Exception as exc:
        render_api_error(exc)
        jobs = []
    if not jobs:
        st.info("还没有保存的岗位，请先分析 JD。")
    else:
        selected = st.selectbox(
            "选择岗位",
            jobs,
            format_func=lambda row: f"{row['id']} | {row['company'] or '未知公司'} | {row['title'] or '未知岗位'}",
        )
        if st.button("生成面试准备", type="primary"):
            try:
                with st.spinner("正在生成面试问题和复习计划..."):
                    prep = api_post(f"/interview/{selected['id']}/generate", timeout=120)
                for title, key in [
                    ("技术问题", "technical_questions"),
                    ("项目深挖", "project_questions"),
                    ("高频追问", "followup_questions"),
                    ("回答要点", "answer_points"),
                    ("三天复习计划", "review_plan"),
                ]:
                    st.subheader(title)
                    for item in prep.get(key, []):
                        st.write(f"- {item}")
                st.subheader("自我介绍建议")
                st.write(prep.get("self_intro_tip", ""))
            except Exception as exc:
                render_api_error(exc)

elif page == "投递看板":
    st.title("投递看板")
    try:
        jobs = api_get("/applications")
    except Exception as exc:
        render_api_error(exc)
        jobs = []
    if not jobs:
        st.info("暂无岗位记录。")
    else:
        st.dataframe(
            [
                {
                    "公司": row["company"],
                    "岗位": row["title"],
                    "匹配度": row["overall_score"],
                    "状态": row["status"],
                    "下一步任务": row["next_step"],
                    "备注": row["notes"],
                }
                for row in jobs
            ],
            use_container_width=True,
        )
        selected = st.selectbox(
            "编辑岗位状态",
            jobs,
            format_func=lambda row: f"{row['id']} | {row['company'] or '未知公司'} | {row['title'] or '未知岗位'}",
        )
        statuses = ["未投递", "已投递", "简历筛选中", "笔试", "一面", "二面", "HR 面", "已拒", "已 offer", "放弃"]
        status = st.selectbox("状态", statuses, index=statuses.index(selected["status"]) if selected["status"] in statuses else 0)
        next_step = st.text_input("下一步任务", value=selected["next_step"] or "")
        notes = st.text_area("备注", value=selected["notes"] or "", height=120)
        if st.button("保存状态", type="primary"):
            try:
                api_patch(f"/applications/{selected['id']}", json={"status": status, "next_step": next_step, "notes": notes})
                st.success("已更新投递状态。")
            except Exception as exc:
                render_api_error(exc)


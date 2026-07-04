from app.agent.state import JobMatchState
from app.db.database import SessionLocal, init_db
from app.schemas.match import MatchReport
from app.services.jd_parser import parse_jd
from app.services.match_scorer import score_match
from app.services.resume_profiler import load_resume_profile
from app.tools.match_advice_tool import enrich_match_report_with_deepseek
from app.tools.persistence_tool import PersistenceTool


def jd_parse_node(state: JobMatchState) -> JobMatchState:
    state["job"] = parse_jd(state["jd_text"])
    return state


def resume_load_node(state: JobMatchState) -> JobMatchState:
    state["resume"] = load_resume_profile(state.get("resume_path"))
    return state


def match_score_node(state: JobMatchState) -> JobMatchState:
    state["report"] = score_match(state["job"], state["resume"])
    return state


def llm_advice_node(state: JobMatchState) -> JobMatchState:
    state["report"] = enrich_match_report_with_deepseek(state["job"], state["resume"], state["report"])
    return state


def gap_analysis_node(state: JobMatchState) -> JobMatchState:
    report = state["report"]
    if not report.weaknesses:
        report.weaknesses.append("暂无明显短板，建议继续核对 JD 中的硬性条件。")
    return state


def recommendation_node(state: JobMatchState) -> JobMatchState:
    report = state["report"]
    if report.overall_score >= 75 and "优先" not in report.recommendation:
        report.recommendation = "建议优先投递。" + report.recommendation
    return state


def save_result_node(state: JobMatchState) -> JobMatchState:
    if not state.get("persist", True):
        return state
    init_db()
    with SessionLocal() as db:
        state["report"] = PersistenceTool().save_job_match(db, state["jd_text"], state["job"], state["report"])
    return state


def build_job_match_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(JobMatchState)
    graph.add_node("jd_parse_node", jd_parse_node)
    graph.add_node("resume_load_node", resume_load_node)
    graph.add_node("match_score_node", match_score_node)
    graph.add_node("llm_advice_node", llm_advice_node)
    graph.add_node("gap_analysis_node", gap_analysis_node)
    graph.add_node("recommendation_node", recommendation_node)
    graph.add_node("save_result_node", save_result_node)

    graph.set_entry_point("jd_parse_node")
    graph.add_edge("jd_parse_node", "resume_load_node")
    graph.add_edge("resume_load_node", "match_score_node")
    graph.add_edge("match_score_node", "llm_advice_node")
    graph.add_edge("llm_advice_node", "gap_analysis_node")
    graph.add_edge("gap_analysis_node", "recommendation_node")
    graph.add_edge("recommendation_node", "save_result_node")
    graph.add_edge("save_result_node", END)
    return graph.compile()


def run_job_match_agent(jd_text: str, resume_path: str | None = None, persist: bool = True) -> MatchReport:
    state: JobMatchState = {"jd_text": jd_text, "resume_path": resume_path, "persist": persist}
    try:
        app = build_job_match_graph()
        result = app.invoke(state)
    except ImportError:
        result = _run_sequential(state)
    return result["report"]


def _run_sequential(state: JobMatchState) -> JobMatchState:
    for node in [
        jd_parse_node,
        resume_load_node,
        match_score_node,
        llm_advice_node,
        gap_analysis_node,
        recommendation_node,
        save_result_node,
    ]:
        state = node(state)
    return state

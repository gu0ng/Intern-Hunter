from app.agent.state import JobMatchState
from app.db.crud import get_latest_match_report, get_latest_match_report_by_jd_hash
from app.db.database import SessionLocal, init_db
from app.schemas.match import MatchReport
from app.services.jd_parser import parse_jd
from app.services.match_scorer import score_match
from app.services.resume_profiler import load_resume_profile
from app.tools.cache_tool import JobCacheTool
from app.tools.hash_utils import compute_jd_hash
from app.tools.match_advice_tool import enrich_match_report_with_deepseek
from app.tools.persistence_tool import PersistenceTool


def _append_note(current: str, note: str) -> str:
    return f"{current} {note}".strip() if current else note


def cache_lookup_node(state: JobMatchState) -> JobMatchState:
    if not state.get("persist", True):
        state["cached"] = False
        return state

    jd_hash = compute_jd_hash(state["jd_text"])
    state["jd_hash"] = jd_hash
    init_db()
    cache = JobCacheTool()
    with SessionLocal() as db:
        cached_job_id = cache.get_job_id(jd_hash)
        if cached_job_id is not None:
            cached_report = get_latest_match_report(db, cached_job_id)
            if cached_report:
                cached_report.score_details["cache_hit"] = "redis_precheck"
                cached_report.llm_notes = _append_note(cached_report.llm_notes, "命中 Redis 前置缓存，已跳过 DeepSeek 解析、评分和建议生成。")
                state["report"] = cached_report
                state["cached"] = True
                state["cache_hit"] = "redis"
                return state

        existing_report = get_latest_match_report_by_jd_hash(db, jd_hash)
        if existing_report:
            if existing_report.job_id is not None:
                cache.set_job_id(jd_hash, existing_report.job_id)
            existing_report.score_details["cache_hit"] = "sqlite_precheck"
            existing_report.llm_notes = _append_note(existing_report.llm_notes, "命中 SQLite 前置去重，已跳过 DeepSeek 解析、评分和建议生成。")
            state["report"] = existing_report
            state["cached"] = True
            state["cache_hit"] = "sqlite"
            return state

    state["cached"] = False
    state["cache_hit"] = "miss"
    return state


def route_after_cache_lookup(state: JobMatchState) -> str:
    return "cached" if state.get("cached") else "miss"


def jd_parse_node(state: JobMatchState) -> JobMatchState:
    state["job"] = parse_jd(state["jd_text"])
    return state


def resume_load_node(state: JobMatchState) -> JobMatchState:
    state["resume"] = load_resume_profile(state.get("resume_path"))
    return state


def match_score_node(state: JobMatchState) -> JobMatchState:
    state["report"] = score_match(state["job"], state["resume"])
    state["report"].score_details["cache_hit"] = state.get("cache_hit", "miss")
    if state.get("jd_hash"):
        state["report"].score_details["jd_hash"] = state["jd_hash"]
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
    graph.add_node("cache_lookup_node", cache_lookup_node)
    graph.add_node("jd_parse_node", jd_parse_node)
    graph.add_node("resume_load_node", resume_load_node)
    graph.add_node("match_score_node", match_score_node)
    graph.add_node("llm_advice_node", llm_advice_node)
    graph.add_node("gap_analysis_node", gap_analysis_node)
    graph.add_node("recommendation_node", recommendation_node)
    graph.add_node("save_result_node", save_result_node)

    graph.set_entry_point("cache_lookup_node")
    graph.add_conditional_edges(
        "cache_lookup_node",
        route_after_cache_lookup,
        {"cached": END, "miss": "jd_parse_node"},
    )
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
    state = cache_lookup_node(state)
    if state.get("cached"):
        return state
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

from langgraph.graph import END, StateGraph

from worker_app.nodes.coverage_analyzer import coverage_analyzer
from worker_app.nodes.missing_test_recommender import missing_test_recommender
from worker_app.nodes.quality_validator import quality_validator
from worker_app.nodes.report_saver import report_saver
from worker_app.nodes.request_validator import request_validator
from worker_app.nodes.requirement_parser import requirement_parser
from worker_app.nodes.requirement_retriever import requirement_retriever
from worker_app.nodes.test_file_classifier import test_file_classifier
from worker_app.nodes.test_file_retriever import test_file_retriever
from worker_app.nodes.test_plan_generator import test_plan_generator
from worker_app.nodes.test_search_planner import test_search_planner
from worker_app.state import AgentState


def _failed_or_continue(state: AgentState) -> str:
    return "end" if state.get("status") == "failed" else "continue"

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("request_validator", request_validator)
    graph.add_node("requirement_retriever", requirement_retriever)
    graph.add_node("requirement_parser", requirement_parser)
    graph.add_node("test_search_planner", test_search_planner)
    graph.add_node("test_file_retriever", test_file_retriever)
    graph.add_node("test_file_classifier", test_file_classifier)
    graph.add_node("coverage_analyzer", coverage_analyzer)
    graph.add_node("test_plan_generator", test_plan_generator)
    graph.add_node("missing_test_recommender", missing_test_recommender)
    graph.add_node("quality_validator", quality_validator)
    graph.add_node("report_saver", report_saver)

    graph.set_entry_point("request_validator")
    graph.add_conditional_edges("request_validator", _failed_or_continue, {"end": END, "continue": "requirement_retriever"})
    # Task 11 redesigned requirement_retriever (per design.md §5.2's REST-fallback decision)
    # to set status="failed" when the direct GitHub issue-body fetch fails — a failure path
    # the plan's original (stale) requirement_retriever snippet never had, since it fetched
    # the body through call_github_tool with no error handling at all. Without this
    # conditional edge, a body-fetch failure would fall through to requirement_parser with
    # state["issue_body"] unset, raising KeyError there instead of failing cleanly.
    graph.add_conditional_edges("requirement_retriever", _failed_or_continue, {"end": END, "continue": "requirement_parser"})
    graph.add_conditional_edges("requirement_parser", _failed_or_continue, {"end": END, "continue": "test_search_planner"})
    graph.add_edge("test_search_planner", "test_file_retriever")
    graph.add_edge("test_file_retriever", "test_file_classifier")
    graph.add_edge("test_file_classifier", "coverage_analyzer")
    graph.add_edge("coverage_analyzer", "test_plan_generator")
    graph.add_edge("test_plan_generator", "missing_test_recommender")
    graph.add_edge("missing_test_recommender", "quality_validator")
    graph.add_edge("quality_validator", "report_saver")
    graph.add_edge("report_saver", END)
    return graph.compile()

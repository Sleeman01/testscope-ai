import logging

from metrics import ANALYSIS_COUNT

from app.mcp_clients import call_test_mcp_tool

logger = logging.getLogger(__name__)


async def report_saver(state: dict) -> dict:
    state["status"] = "completed"
    try:
        await call_test_mcp_tool(
            "save_coverage_report", analysis_id=state["analysis_id"], repository=state["repository"],
            issue_number=state["issue_number"], requirement=state["requirement"],
            coverage_matrix=state["coverage_matrix"], missing_tests=state["missing_tests"],
            test_plan=state["test_plan"], status=state["status"], tool_call_trace=state.get("tool_call_trace", []),
        )
        state["storage_status"] = "saved"
    except Exception as exc:
        logger.exception("save_coverage_report failed for analysis_id=%s", state["analysis_id"])
        state["storage_status"] = "failed"
        state.setdefault("warnings", []).append(f"Report save failed: {exc}")
    ANALYSIS_COUNT.labels(status=state["status"]).inc()
    return state

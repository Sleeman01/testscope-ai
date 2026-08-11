import logging

from worker_app.mcp_clients import call_test_mcp_tool

logger = logging.getLogger(__name__)


async def test_file_retriever(state: dict) -> dict:
    try:
        result = await call_test_mcp_tool(
            "find_test_files", analysis_id=state["analysis_id"], repository=state["repository"],
            ref=state["default_branch"], keywords=state["search_keywords"],
        )
        state["candidate_files"] = result["files"]
    except Exception as exc:
        logger.exception(
            "find_test_files failed for analysis_id=%s", state["analysis_id"],
            extra={
                "analysis_id": state["analysis_id"], "repository": state.get("repository"),
                "node": "test_file_retriever", "tool": "find_test_files", "error_type": type(exc).__name__,
            },
        )
        state["candidate_files"] = []
        state.setdefault("warnings", []).append(f"find_test_files failed; continuing with no candidate files: {exc}")
    return state

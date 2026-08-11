import logging

from worker_app.mcp_clients import call_test_mcp_tool

logger = logging.getLogger(__name__)


async def test_file_classifier(state: dict) -> dict:
    metadata = {}
    for candidate in state["candidate_files"]:
        path = candidate["path"]
        try:
            result = await call_test_mcp_tool("extract_test_metadata", analysis_id=state["analysis_id"], path=path)
            metadata[path] = result["tests"]
        except Exception:
            logger.exception("Could not parse %s", path)
            state.setdefault("warnings", []).append(f"Could not parse {path}; skipped.")
    state["test_metadata"] = metadata
    return state

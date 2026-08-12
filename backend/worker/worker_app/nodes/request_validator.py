# search_repositories is the confirmed substitute for the non-existent get_repository
# tool (design.md §5.2) — a search endpoint, not a direct per-repo lookup, so a "not
# found" repo surfaces as a zero-item result rather than a tool-level error.
import logging

from repository import InvalidRepositoryError, normalize_repository

from worker_app.mcp_clients import call_github_tool

logger = logging.getLogger(__name__)


async def request_validator(state: dict) -> dict:
    # Defensive even though backend/api's CreateAnalysisRequest already normalizes
    # repository input at request time — a malformed value here (e.g. a raw GitHub URL)
    # used to reach a bare `.split("/", 1)`, producing a nonsense MCP search query whose
    # non-JSON error response then raised deep inside anyio's TaskGroup, hiding the real
    # cause. Fail cleanly here regardless of what upstream guarantees.
    try:
        owner, repo = normalize_repository(state["repository"]).split("/", 1)
    except InvalidRepositoryError as exc:
        state["status"] = "failed"
        state["error_message"] = str(exc)
        return state
    try:
        result = await call_github_tool(
            "search_repositories", query=f"repo:{owner}/{repo}", minimal_output=False,
        )
    except Exception as exc:
        logger.exception(
            "Repository validation failed for %s", state["repository"],
            extra={
                "analysis_id": state.get("analysis_id"), "repository": state["repository"],
                "issue_number": state.get("issue_number"), "node": "request_validator",
                "status": "failed", "error_type": type(exc).__name__,
            },
        )
        state["status"] = "failed"
        state["error_message"] = f"Repository validation failed: {exc}"
        return state
    items = result.get("items", [])
    if not items:
        state["status"] = "failed"
        state["error_message"] = f"Repository not found: {state['repository']}"
        return state
    state["default_branch"] = items[0].get("default_branch", "main")
    return state

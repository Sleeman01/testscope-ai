# search_repositories is the confirmed substitute for the non-existent get_repository
# tool (design.md §5.2) — a search endpoint, not a direct per-repo lookup, so a "not
# found" repo surfaces as a zero-item result rather than a tool-level error.
import logging

from app.mcp_clients import call_github_tool

logger = logging.getLogger(__name__)


async def request_validator(state: dict) -> dict:
    owner, repo = state["repository"].split("/", 1)
    try:
        result = await call_github_tool(
            "search_repositories", query=f"repo:{owner}/{repo}", minimal_output=False,
        )
    except Exception as exc:
        logger.exception("Repository validation failed for %s", state["repository"])
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

# Issue-body fetch bypasses MCP entirely (design.md §5.2's standing decision): no tool
# on the deployed github-mcp-server returns a single issue's body by direct lookup, so
# this hits the GitHub REST API directly with the same token mcp-github would otherwise
# receive (same os.environ["GITHUB_TOKEN"] convention as mcp-server/github_client.py).
# Comments have a working MCP substitute (issue_read/get_comments) and still route
# through call_github_tool for its retry/classification behavior.
import os
import httpx2
from app.mcp_clients import call_github_tool

GITHUB_API_BASE = "https://api.github.com"

async def _fetch_issue_body(owner: str, repo: str, issue_number: int, github_token: str | None = None) -> str:
    token = github_token or os.environ["GITHUB_TOKEN"]
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}"
    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json().get("body") or ""

async def requirement_retriever(state: dict) -> dict:
    owner, repo = state["repository"].split("/", 1)
    try:
        state["issue_body"] = await _fetch_issue_body(owner, repo, state["issue_number"])
    except Exception as exc:
        state["status"] = "failed"
        state["error_message"] = f"Could not fetch issue body: {exc}"
        return state
    try:
        comments = await call_github_tool(
            "issue_read", method="get_comments", owner=owner, repo=repo,
            issue_number=state["issue_number"],
        )
        state["issue_comments"] = [c.get("body", "") for c in comments.get("comments", [])]
    except Exception:
        state["issue_comments"] = []
        state.setdefault("warnings", []).append("Could not fetch issue comments; analyzing issue body only.")
    return state

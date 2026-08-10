import json
import os

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class GithubClient:
    """Thin MCP client this server uses to call the separately-deployed mcp-github server.

    TOOL_NAME confirmed against the real deployed github-mcp-server in Task 8's Step 1 —
    get_repository does not exist on the deployed server (v1.8.0); search_repositories is
    the confirmed substitute (see design.md §5.2). If the installed image's tool set ever
    changes, re-run scripts/verify-github-mcp-tools.py and update this constant.
    """
    TOOL_NAME = "search_repositories"

    def __init__(self, base_url: str | None = None, github_token: str | None = None):
        self.base_url = base_url or os.environ["MCP_GITHUB_URL"]
        self.github_token = github_token or os.environ["GITHUB_TOKEN"]

    async def get_repo_size_bytes(self, owner: str, repo: str) -> int:
        http_client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {self.github_token}"})
        async with (
            streamable_http_client(self.base_url, http_client=http_client) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(self.TOOL_NAME, {
                "query": f"repo:{owner}/{repo}", "minimal_output": False,
            })
            # This server leaves structured_content as None; payload is JSON text
            # in content[0].text instead (confirmed in Task 8's verification).
            text = next(b.text for b in result.content if getattr(b, "text", None))
            items = json.loads(text).get("items", [])
            if not items:
                raise ValueError(f"search_repositories found no match for {owner}/{repo}")
            size_kb = items[0]["size"]
            return size_kb * 1024

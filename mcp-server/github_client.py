import os

class GithubClient:
    """Thin MCP client this server uses to call the separately-deployed mcp-github server.

    Interface stub (Task 3) — real implementation filled in Task 8, once the deployed
    github-mcp-server's actual tool name/response shape is confirmed.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ.get("MCP_GITHUB_URL")

    async def get_repo_size_bytes(self, owner: str, repo: str) -> int:
        raise NotImplementedError("Real implementation added in Task 8")

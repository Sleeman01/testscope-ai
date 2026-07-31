# Run once by hand, not part of any automated test. Requires a running github-mcp-server
# started in HTTP mode (the bare image invocation defaults to stdio, which exits
# immediately if run detached):
#   docker run -d --name mcp-github-verify -p 8101:8100 \
#     -e GITHUB_PERSONAL_ACCESS_TOKEN=<your-read-only-PAT> \
#     ghcr.io/github/github-mcp-server:latest http --port 8100 --listen-host 0.0.0.0
# HTTP mode requires the token as an Authorization: Bearer header per request (the env
# var above is only used at container startup, not read for request auth) — see
# docs/2026-07-30-testscope-ai-design.md §5.2 for the full verification record.
import asyncio
import json
import os
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ASSUMED_TOOLS = {
    "get_repository": {"owner": "octocat", "repo": "Hello-World"},
    "get_issue": {"owner": "octocat", "repo": "Hello-World", "issue_number": 1},
    "get_issue_comments": {"owner": "octocat", "repo": "Hello-World", "issue_number": 1},
}

async def main():
    token = os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]
    http_client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"})
    async with streamable_http_client("http://localhost:8101/mcp", http_client=http_client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            listed_names = {t.name for t in listed.tools}
            print("Tools exposed by this server:", sorted(listed_names))
            for name in [*ASSUMED_TOOLS, "create_issue"]:
                print(f"  {'FOUND' if name in listed_names else 'MISSING'}: {name}")

            for tool_name, args in ASSUMED_TOOLS.items():
                result = await session.call_tool(tool_name, args)
                print(f"\n{tool_name}({args}) ->")
                print(json.dumps(result.structured_content, indent=2))

            # create_issue is deliberately NOT called here (it would create a real GitHub
            # issue) — instead, print its declared input schema so field names (e.g. does
            # it return `html_url` on success?) can be checked against the official docs
            # for the installed image version without side effects.
            create_issue_tool = next(t for t in listed.tools if t.name == "create_issue")
            print("\ncreate_issue input schema:")
            print(json.dumps(create_issue_tool.input_schema, indent=2))

asyncio.run(main())

import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from config import get_settings

async def call_github_tool(tool_name: str, **kwargs) -> dict:
    async with streamable_http_client(get_settings().mcp_github_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, kwargs)
            # structured_content is None for this server's dict-returning tools
            # (design.md §5.2) — parse the JSON text payload instead, same fix as
            # backend/worker/app/mcp_clients.py._call_once.
            text = next(b.text for b in result.content if getattr(b, "text", None))
            return json.loads(text)

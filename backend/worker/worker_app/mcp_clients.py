import json
import time

from config import get_settings
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from metrics import MCP_TOOL_CALL_COUNT, MCP_TOOL_LATENCY

from retry import with_retry

TERMINAL_MARKERS = ("404", "not found", "403", "access denied", "422", "invalid")

def _is_retryable_tool_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return not any(marker in message for marker in TERMINAL_MARKERS)

async def _call_once(base_url: str, tool_name: str, kwargs: dict) -> dict:
    async with (
        streamable_http_client(base_url) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        result = await session.call_tool(tool_name, kwargs)
        # structured_content is None for these servers' dict-returning tools
        # (design.md §5.2) — parse the JSON text payload instead, same as
        # mcp-server/github_client.py.
        text = next(b.text for b in result.content if getattr(b, "text", None))
        return json.loads(text)

async def _call(base_url: str, tool_name: str, **kwargs) -> dict:
    # Task 39's plan snippet reimplements this whole function around a bare
    # streamable_http_client/ClientSession call (and result.structured_content, which
    # design.md §5.2 already established returns None for these servers) — the same class
    # of staleness Task 11 already found and fixed once. Instrumenting around the real
    # with_retry(_call_once, ...) call instead: one count/latency sample per logical tool
    # call (post-retry), not per individual transport attempt, so a transient-error retry
    # that eventually succeeds is recorded once as "success," not as an extra "error".
    start = time.time()
    status = "success"
    try:
        return await with_retry(
            _call_once, base_url, tool_name, kwargs,
            max_attempts=3, backoff_base=1.0, is_retryable=_is_retryable_tool_error,
        )
    except Exception:
        status = "error"
        raise
    finally:
        MCP_TOOL_LATENCY.labels(tool=tool_name).observe(time.time() - start)
        MCP_TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()

async def call_github_tool(tool_name: str, **kwargs) -> dict:
    return await _call(get_settings().mcp_github_url, tool_name, **kwargs)

async def call_test_mcp_tool(tool_name: str, **kwargs) -> dict:
    return await _call(get_settings().mcp_test_analysis_url, tool_name, **kwargs)

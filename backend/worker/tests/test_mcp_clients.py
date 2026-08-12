from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from config import get_settings
from worker_app.mcp_clients import (
    McpNonJsonResponseError,
    _is_retryable_tool_error,
    call_github_tool,
    call_test_mcp_tool,
)


def _fake_result(text: str):
    result = MagicMock()
    result.content = [MagicMock(text=text)]
    return result

@pytest.fixture(autouse=True)
def _settings_env(monkeypatch):
    # get_settings() requires all Settings fields even though these tests only need
    # mcp_github_url; same monkeypatch + cache_clear pattern as backend/shared's
    # test_config.py, since get_settings is @lru_cache'd across the whole test session.
    monkeypatch.setenv("DYNAMODB_TABLE", "unused-in-this-test")
    monkeypatch.setenv("S3_BUCKET", "unused-in-this-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused-in-this-test")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github:8100")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "unused-in-this-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_retries_transient_tool_error_then_succeeds():
    calls = {"count": 0}
    async def fake_call_once(base_url, tool_name, kwargs):
        calls["count"] += 1
        if calls["count"] < 2:
            raise TimeoutError("connection reset")
        return {"default_branch": "main"}
    with patch("worker_app.mcp_clients._call_once", new=AsyncMock(side_effect=fake_call_once)):
        result = await call_github_tool("get_repository", owner="acme", repo="widgets")
    assert result == {"default_branch": "main"}
    assert calls["count"] == 2

@pytest.mark.asyncio
async def test_does_not_retry_not_found_error():
    calls = {"count": 0}
    async def fake_call_once(base_url, tool_name, kwargs):
        calls["count"] += 1
        raise RuntimeError("404 Not Found")
    with (
        patch("worker_app.mcp_clients._call_once", new=AsyncMock(side_effect=fake_call_once)),
        pytest.raises(RuntimeError, match="404"),
    ):
        await call_github_tool("get_repository", owner="acme", repo="does-not-exist")
    assert calls["count"] == 1

def test_classifier_treats_terminal_markers_as_non_retryable():
    assert _is_retryable_tool_error(Exception("404 Not Found")) is False
    assert _is_retryable_tool_error(Exception("403 access denied")) is False
    assert _is_retryable_tool_error(TimeoutError("connection timed out")) is True
    assert _is_retryable_tool_error(Exception("500 Internal Server Error")) is True

def test_classifier_treats_non_json_response_as_non_retryable():
    # A malformed-query error (e.g. from a bad search string) comes back as a non-JSON
    # body with no "404"/"403"/etc marker in it — retrying the identical malformed
    # request 3 times is pointless, since it'll fail the same way every time.
    assert _is_retryable_tool_error(McpNonJsonResponseError("boom")) is False

@pytest.mark.asyncio
async def test_call_once_raises_readable_error_on_non_json_response():
    # Real bug: a non-JSON response used to hit json.loads(text) directly, indistinguishable
    # from a transport failure once anyio wrapped it in nested ExceptionGroups — cost hours
    # of debugging. The raised error must surface the actual response body.
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(
        return_value=_fake_result("<html>502 Bad Gateway from upstream proxy</html>"),
    )
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session

    transport_cm = AsyncMock()
    transport_cm.__aenter__.return_value = (AsyncMock(), AsyncMock())

    with patch("worker_app.mcp_clients.streamable_http_client", return_value=transport_cm), \
         patch("worker_app.mcp_clients.ClientSession", return_value=session_cm), \
         pytest.raises(McpNonJsonResponseError) as exc_info:
        await call_github_tool("search_repositories", query="repo:acme/widgets")

    assert "search_repositories" in str(exc_info.value)
    assert "502 Bad Gateway" in str(exc_info.value)

@pytest.mark.asyncio
async def test_non_json_response_is_not_retried():
    calls = {"count": 0}
    async def fake_call_once(base_url, tool_name, kwargs):
        calls["count"] += 1
        raise McpNonJsonResponseError("non-JSON response from tool 'x': 'oops'")
    with (
        patch("worker_app.mcp_clients._call_once", new=AsyncMock(side_effect=fake_call_once)),
        pytest.raises(McpNonJsonResponseError),
    ):
        await call_github_tool("search_repositories", query="repo:acme/widgets")
    assert calls["count"] == 1

@pytest.mark.asyncio
async def test_call_once_parses_json_text_payload_over_the_real_mcp_transport():
    # _call_once itself is mocked out by every test above (matching plan.md's own
    # design) — closes the resulting coverage gap on its actual transport/JSON-parsing
    # logic, same mocking-the-transport-boundary approach as
    # mcp-server/tests/test_github_client.py (structured_content is None for these
    # servers per design.md §5.2, so this is the code path real traffic takes).
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=_fake_result('{"default_branch": "main"}'))
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session

    transport_cm = AsyncMock()
    transport_cm.__aenter__.return_value = (AsyncMock(), AsyncMock())

    with patch("worker_app.mcp_clients.streamable_http_client", return_value=transport_cm), \
         patch("worker_app.mcp_clients.ClientSession", return_value=session_cm):
        result = await call_github_tool("get_repository", owner="acme", repo="widgets")

    assert result == {"default_branch": "main"}
    session.call_tool.assert_awaited_once_with(
        "get_repository", {"owner": "acme", "repo": "widgets"}
    )

@pytest.mark.asyncio
async def test_call_test_mcp_tool_routes_to_the_test_analysis_mcp_url():
    # No node in Task 11 calls this yet (Tasks 13/14/15/17 do) — a direct test closes
    # the gap rather than leaving it uncovered until those tasks exist.
    async def fake_call_once(base_url, tool_name, kwargs):
        assert base_url == "unused-in-this-test"
        return {"tests": []}
    with patch("worker_app.mcp_clients._call_once", new=AsyncMock(side_effect=fake_call_once)):
        result = await call_test_mcp_tool("extract_test_metadata", path="tests/test_x.py")
    assert result == {"tests": []}

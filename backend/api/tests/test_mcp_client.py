from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from config import get_settings

from app.mcp_client import call_github_tool


def _fake_result(text: str):
    result = MagicMock()
    result.content = [MagicMock(text=text)]
    return result

@pytest.fixture(autouse=True)
def _settings_env(monkeypatch):
    # get_settings() requires all Settings fields even though this test only needs
    # mcp_github_url; same monkeypatch + cache_clear pattern as backend/worker's
    # test_mcp_clients.py, since get_settings is @lru_cache'd across the whole test session.
    monkeypatch.setenv("DYNAMODB_TABLE", "unused-in-this-test")
    monkeypatch.setenv("S3_BUCKET", "unused-in-this-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused-in-this-test")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github:8100")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "unused-in-this-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_call_github_tool_parses_json_text_payload_over_the_real_mcp_transport():
    # Every route test mocks call_github_tool out entirely (matching plan.md's own
    # design, and Task 17's patch-the-consumer's-local-name lesson) — closes the
    # resulting coverage gap on its actual transport/JSON-parsing logic, same
    # mocking-the-transport-boundary approach as backend/worker's own
    # test_call_once_parses_json_text_payload_over_the_real_mcp_transport (Task 11).
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=_fake_result('{"html_url": "https://github.com/acme/widgets/issues/99"}'))
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session

    transport_cm = AsyncMock()
    transport_cm.__aenter__.return_value = (AsyncMock(), AsyncMock())

    with patch("app.mcp_client.streamable_http_client", return_value=transport_cm), \
         patch("app.mcp_client.ClientSession", return_value=session_cm):
        result = await call_github_tool("issue_write", method="create", owner="acme", repo="widgets")

    assert result == {"html_url": "https://github.com/acme/widgets/issues/99"}
    session.call_tool.assert_awaited_once_with(
        "issue_write", {"method": "create", "owner": "acme", "repo": "widgets"}
    )

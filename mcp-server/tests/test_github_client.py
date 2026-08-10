from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_client import GithubClient


def _fake_result(text: str):
    result = MagicMock()
    result.content = [MagicMock(text=text)]
    return result


@pytest.mark.asyncio
async def test_get_repo_size_bytes_parses_kb_to_bytes(monkeypatch):
    monkeypatch.setenv("MCP_GITHUB_URL", "http://localhost:1/mcp")
    monkeypatch.setenv("GITHUB_TOKEN", "unused")
    client = GithubClient()

    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=_fake_result(
        '{"items": [{"default_branch": "main", "size": 2048}]}'
    ))
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session

    transport_cm = AsyncMock()
    transport_cm.__aenter__.return_value = (AsyncMock(), AsyncMock())

    with patch("github_client.streamable_http_client", return_value=transport_cm), \
         patch("github_client.ClientSession", return_value=session_cm):
        size_bytes = await client.get_repo_size_bytes("acme", "widgets")

    assert size_bytes == 2048 * 1024
    session.call_tool.assert_awaited_once_with(
        "search_repositories", {"query": "repo:acme/widgets", "minimal_output": False}
    )


@pytest.mark.asyncio
async def test_get_repo_size_bytes_raises_when_no_match(monkeypatch):
    monkeypatch.setenv("MCP_GITHUB_URL", "http://localhost:1/mcp")
    monkeypatch.setenv("GITHUB_TOKEN", "unused")
    client = GithubClient()

    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=_fake_result('{"items": []}'))
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session

    transport_cm = AsyncMock()
    transport_cm.__aenter__.return_value = (AsyncMock(), AsyncMock())

    with (
        patch("github_client.streamable_http_client", return_value=transport_cm),
        patch("github_client.ClientSession", return_value=session_cm),
        pytest.raises(ValueError, match="no match"),
    ):
        await client.get_repo_size_bytes("acme", "does-not-exist")

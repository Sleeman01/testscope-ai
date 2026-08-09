import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.nodes.requirement_retriever import requirement_retriever, _fetch_issue_body

@pytest.mark.asyncio
async def test_retrieves_issue_body_and_comments():
    state = {"repository": "acme/widgets", "issue_number": 42, "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.requirement_retriever._fetch_issue_body", new=AsyncMock(return_value="Add login")), \
         patch("app.nodes.requirement_retriever.call_github_tool",
               new=AsyncMock(return_value={"comments": [{"body": "clarification"}]})):
        result = await requirement_retriever(state)
    assert result["issue_body"] == "Add login"
    assert result["issue_comments"] == ["clarification"]

@pytest.mark.asyncio
async def test_falls_back_to_body_only_when_comments_fail():
    state = {"repository": "acme/widgets", "issue_number": 42, "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.requirement_retriever._fetch_issue_body", new=AsyncMock(return_value="Add login")), \
         patch("app.nodes.requirement_retriever.call_github_tool",
               new=AsyncMock(side_effect=Exception("comments API failed"))):
        result = await requirement_retriever(state)
    assert result["issue_body"] == "Add login"
    assert result["issue_comments"] == []
    assert any("comment" in w.lower() for w in result["warnings"])

@pytest.mark.asyncio
async def test_fails_gracefully_when_issue_body_fetch_fails():
    # Unlike comments, there's no documented fallback for a failed body fetch
    # (design.md §4's Requirement Retriever row only covers comments-fetch failure) —
    # mirrors request_validator's own explicit catch-and-fail pattern.
    state = {"repository": "acme/widgets", "issue_number": 42, "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.requirement_retriever._fetch_issue_body",
               new=AsyncMock(side_effect=Exception("404 Not Found"))):
        result = await requirement_retriever(state)
    assert result["status"] == "failed"
    assert "issue body" in result["error_message"].lower() or "404" in result["error_message"]

@pytest.mark.asyncio
async def test_fetch_issue_body_calls_the_real_github_rest_api(monkeypatch):
    # _fetch_issue_body itself is mocked out by every test above — closes the resulting
    # coverage gap on its actual REST-call logic, same mocking-the-transport-boundary
    # approach used for app/mcp_clients.py's _call_once and
    # mcp-server/tests/test_github_client.py.
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"body": "Add login"}

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client_cm = AsyncMock()
    client_cm.__aenter__.return_value = client

    with patch("app.nodes.requirement_retriever.httpx2.AsyncClient", return_value=client_cm) as mock_client_cls:
        body = await _fetch_issue_body("acme", "widgets", 42)

    assert body == "Add login"
    mock_client_cls.assert_called_once_with(headers={"Authorization": "Bearer test-token"})
    client.get.assert_awaited_once_with("https://api.github.com/repos/acme/widgets/issues/42")

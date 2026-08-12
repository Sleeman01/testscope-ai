from unittest.mock import AsyncMock, patch

import pytest

from worker_app.nodes.request_validator import request_validator


@pytest.mark.asyncio
async def test_sets_default_branch_on_success():
    state = {"repository": "acme/widgets", "tool_call_trace": [], "warnings": []}
    with patch(
        "worker_app.nodes.request_validator.call_github_tool",
        new=AsyncMock(return_value={"items": [{"default_branch": "main", "size": 100}]}),
    ):
        result = await request_validator(state)
    assert result["default_branch"] == "main"
    assert result.get("status") != "failed"

@pytest.mark.asyncio
async def test_fails_gracefully_when_search_returns_zero_items():
    # search_repositories is a search endpoint, not a direct lookup — a real "not found"
    # surfaces as an empty items list, not an exception (design.md §5.2).
    state = {"repository": "acme/does-not-exist", "tool_call_trace": [], "warnings": []}
    with patch(
        "worker_app.nodes.request_validator.call_github_tool",
        new=AsyncMock(return_value={"items": []}),
    ):
        result = await request_validator(state)
    assert result["status"] == "failed"
    assert "not found" in result["error_message"].lower()

@pytest.mark.asyncio
async def test_fails_gracefully_on_tool_error():
    state = {"repository": "acme/does-not-exist", "tool_call_trace": [], "warnings": []}
    with patch(
        "worker_app.nodes.request_validator.call_github_tool",
        new=AsyncMock(side_effect=Exception("403 access denied")),
    ):
        result = await request_validator(state)
    assert result["status"] == "failed"
    assert "403" in result["error_message"] or "access denied" in result["error_message"].lower()

@pytest.mark.asyncio
async def test_normalizes_github_url_instead_of_crashing():
    # Real bug: a full GitHub URL slipping through (e.g. a pre-normalization record)
    # used to hit a bare `.split("/", 1)` here, producing owner="https:" and a malformed
    # MCP search query whose non-JSON error response then raised deep inside anyio's
    # TaskGroup — invisible root cause. request_validator now normalizes it itself,
    # regardless of what upstream (backend/api) already guarantees.
    state = {
        "repository": "https://github.com/acme/widgets",
        "tool_call_trace": [], "warnings": [],
    }
    with patch(
        "worker_app.nodes.request_validator.call_github_tool",
        new=AsyncMock(return_value={"items": [{"default_branch": "main"}]}),
    ) as mock_call:
        result = await request_validator(state)
    assert result.get("status") != "failed"
    mock_call.assert_awaited_once_with(
        "search_repositories", query="repo:acme/widgets", minimal_output=False,
    )

@pytest.mark.asyncio
async def test_fails_gracefully_on_unparseable_repository_instead_of_crashing():
    # A value normalize_repository itself can't make sense of (no slash, no known URL
    # form) must fail cleanly here, not raise past request_validator.
    state = {"repository": "not-a-repo", "tool_call_trace": [], "warnings": []}
    with patch(
        "worker_app.nodes.request_validator.call_github_tool",
        new=AsyncMock(side_effect=AssertionError("call_github_tool must not be called")),
    ):
        result = await request_validator(state)
    assert result["status"] == "failed"
    assert "Invalid repository" in result["error_message"]

import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.request_validator import request_validator

@pytest.mark.asyncio
async def test_sets_default_branch_on_success():
    state = {"repository": "acme/widgets", "tool_call_trace": [], "warnings": []}
    with patch(
        "app.nodes.request_validator.call_github_tool",
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
        "app.nodes.request_validator.call_github_tool",
        new=AsyncMock(return_value={"items": []}),
    ):
        result = await request_validator(state)
    assert result["status"] == "failed"
    assert "not found" in result["error_message"].lower()

@pytest.mark.asyncio
async def test_fails_gracefully_on_tool_error():
    state = {"repository": "acme/does-not-exist", "tool_call_trace": [], "warnings": []}
    with patch(
        "app.nodes.request_validator.call_github_tool",
        new=AsyncMock(side_effect=Exception("403 access denied")),
    ):
        result = await request_validator(state)
    assert result["status"] == "failed"
    assert "403" in result["error_message"] or "access denied" in result["error_message"].lower()

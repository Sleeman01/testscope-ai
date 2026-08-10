from unittest.mock import AsyncMock, patch

import pytest

from app.nodes.test_file_retriever import test_file_retriever

# See test_test_search_planner.py's comment: the imported node function's name matches
# pytest's test_* discovery glob and would otherwise be collected as a test case itself.
test_file_retriever.__test__ = False

@pytest.mark.asyncio
async def test_populates_candidate_files():
    state = {"repository": "acme/widgets", "default_branch": "main", "analysis_id": "a1",
             "search_keywords": ["login"], "tool_call_trace": [], "warnings": []}
    fake_response = {"files": [{"path": "tests/test_login.py", "size_bytes": 100, "matched_keywords": ["login"]}]}
    with patch("app.nodes.test_file_retriever.call_test_mcp_tool", new=AsyncMock(return_value=fake_response)):
        result = await test_file_retriever(state)
    assert result["candidate_files"] == fake_response["files"]

@pytest.mark.asyncio
async def test_no_matches_is_not_a_failure():
    state = {"repository": "acme/widgets", "default_branch": "main", "analysis_id": "a1",
             "search_keywords": ["nonexistent"], "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.test_file_retriever.call_test_mcp_tool", new=AsyncMock(return_value={"files": []})):
        result = await test_file_retriever(state)
    assert result["candidate_files"] == []
    assert result.get("status") != "failed"

@pytest.mark.asyncio
async def test_search_failure_is_non_fatal():
    state = {"repository": "acme/widgets", "default_branch": "main", "analysis_id": "a1",
             "search_keywords": ["login"], "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.test_file_retriever.call_test_mcp_tool", new=AsyncMock(side_effect=Exception("mcp-test-analysis unreachable"))):
        result = await test_file_retriever(state)
    assert result["candidate_files"] == []
    assert result.get("status") != "failed"
    assert any("find_test_files" in w.lower() or "search" in w.lower() for w in result["warnings"])

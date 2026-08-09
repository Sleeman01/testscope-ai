import pytest
from unittest.mock import AsyncMock, patch
from app.nodes.test_search_planner import test_search_planner, SearchKeywords

# The imported node function's name matches pytest's test_* discovery glob — without
# this, pytest tries to collect and run it directly as a test case too (it takes a
# `state` positional arg pytest can't resolve as a fixture).
test_search_planner.__test__ = False

@pytest.mark.asyncio
async def test_generates_keywords_from_criteria():
    state = {"requirement": {"acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}]},
             "tool_call_trace": [], "warnings": []}
    stub = SearchKeywords(keywords=["login", "password", "401"])
    with patch("app.nodes.test_search_planner.call_llm", new=AsyncMock(return_value=stub)):
        result = await test_search_planner(state)
    assert result["search_keywords"] == ["login", "password", "401"]

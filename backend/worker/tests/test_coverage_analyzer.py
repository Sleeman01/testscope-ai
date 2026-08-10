from unittest.mock import AsyncMock, patch

import pytest

from app.nodes.coverage_analyzer import CoverageEntry, coverage_analyzer


@pytest.mark.asyncio
async def test_classifies_each_criterion():
    state = {
        "requirement": {"acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}]},
        "test_metadata": {"tests/test_login.py": [{"name": "test_login_rejects_invalid_password", "assert_count": 1}]},
        "candidate_files": [{"path": "tests/test_login.py"}],
        "analysis_id": "a1", "tool_call_trace": [], "warnings": [],
    }
    stub = [CoverageEntry(criterion_id="AC1", status="Covered",
                           evidence=["tests/test_login.py::test_login_rejects_invalid_password"],
                           explanation="Test asserts 401 on invalid password.")]
    with patch("app.nodes.coverage_analyzer.call_llm", new=AsyncMock(return_value=stub)):
        result = await coverage_analyzer(state)
    assert result["coverage_matrix"][0]["status"] == "Covered"

@pytest.mark.asyncio
async def test_flags_unsupported_framework_when_files_found_but_none_parsed():
    state = {
        "requirement": {"acceptance_criteria": [{"id": "AC1", "text": "x"}]},
        "test_metadata": {}, "candidate_files": [{"path": "tests/login.test.js"}],
        "analysis_id": "a1", "tool_call_trace": [], "warnings": [],
    }
    stub = [CoverageEntry(criterion_id="AC1", status="Unable to determine", evidence=[], explanation="No pytest tests found.")]
    with patch("app.nodes.coverage_analyzer.call_llm", new=AsyncMock(return_value=stub)):
        result = await coverage_analyzer(state)
    assert any("no supported test framework" in w.lower() for w in result["warnings"])

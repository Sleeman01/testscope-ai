from unittest.mock import AsyncMock, patch

import pytest

from app.nodes.test_file_classifier import test_file_classifier

# See test_test_search_planner.py's comment: the imported node function's name matches
# pytest's test_* discovery glob and would otherwise be collected as a test case itself.
test_file_classifier.__test__ = False

@pytest.mark.asyncio
async def test_extracts_metadata_per_candidate_file():
    state = {"analysis_id": "a1", "candidate_files": [{"path": "tests/test_login.py"}],
             "tool_call_trace": [], "warnings": []}
    fake_meta = {"tests": [{"name": "test_login_rejects_invalid_password"}]}
    with patch("app.nodes.test_file_classifier.call_test_mcp_tool", new=AsyncMock(return_value=fake_meta)):
        result = await test_file_classifier(state)
    assert result["test_metadata"]["tests/test_login.py"] == fake_meta["tests"]

@pytest.mark.asyncio
async def test_skips_unparseable_file_without_failing():
    state = {"analysis_id": "a1", "candidate_files": [{"path": "tests/broken.py"}],
              "tool_call_trace": [], "warnings": []}
    with patch("app.nodes.test_file_classifier.call_test_mcp_tool", new=AsyncMock(side_effect=Exception("SyntaxError"))):
        result = await test_file_classifier(state)
    assert result["test_metadata"] == {}
    assert any("broken.py" in w for w in result["warnings"])

from unittest.mock import AsyncMock, patch

import pytest

from app.nodes.report_saver import report_saver


@pytest.mark.asyncio
async def test_marks_completed_on_successful_save():
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42,
              "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "missing_tests": [],
              "test_plan": [], "tool_call_trace": [], "warnings": [], "status": "running"}
    with patch("app.nodes.report_saver.call_test_mcp_tool", new=AsyncMock(return_value={"s3_report_key": "k", "dynamodb_status": "saved"})):
        result = await report_saver(state)
    assert result["status"] == "completed"
    assert result["s3_report_key"] == "k"

@pytest.mark.asyncio
async def test_save_failure_is_non_fatal():
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42,
              "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "missing_tests": [],
              "test_plan": [], "tool_call_trace": [], "warnings": [], "status": "running"}
    with patch("app.nodes.report_saver.call_test_mcp_tool", new=AsyncMock(side_effect=Exception("S3 down"))):
        result = await report_saver(state)
    assert result["status"] == "completed"  # analysis itself still succeeded
    assert result.get("storage_status") == "failed"
    assert any("s3" in w.lower() or "save" in w.lower() for w in result["warnings"])

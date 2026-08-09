import boto3
import pytest
from moto import mock_aws
from unittest.mock import AsyncMock, patch
from config import get_settings
from app.runner import run_analysis
from dynamodb import AnalysisStore

@pytest.fixture
def store_env(monkeypatch):
    # get_settings() is @lru_cache'd process-wide (same issue test_mcp_clients.py already
    # fixes) — without cache_clear() before AND after, this test's DYNAMODB_TABLE="t" can
    # leak into (or be leaked into by) any other test in the same session that also calls
    # run_analysis/get_settings, e.g. test_runner_e2e.py — confirmed by running the full
    # suite: test_runner_e2e.py failed with ResourceNotFoundException (PutItem against
    # table "t", which only this test's moto context creates) once this file ran first.
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "t")
    monkeypatch.setenv("S3_BUCKET", "unused")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused")
    monkeypatch.setenv("MCP_GITHUB_URL", "unused")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "unused")
    get_settings.cache_clear()
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="t", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_run_analysis_marks_failed_and_still_cleans_up_on_graph_exception(store_env):
    # test_runner_e2e.py only exercises the happy path over the real graph/subprocess —
    # this is the entire point of Task 17's own timeout/exception wrapping (run_analysis's
    # try/except/finally), so it's worth a dedicated, fast, fully-mocked test rather than
    # leaving it uncovered: a hung/crashed graph must still mark the analysis failed and
    # still attempt cleanup, not leave the job stuck or skip cleanup entirely.
    with patch("app.runner._graph") as mock_graph, \
         patch("app.runner.call_test_mcp_tool", new=AsyncMock(side_effect=Exception("cleanup also unreachable"))) as mock_cleanup:
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
        await run_analysis(analysis_id="r1", repository="acme/widgets", issue_number=1, notes=None)

    mock_cleanup.assert_awaited_once_with("cleanup_workspace", analysis_id="r1")
    store = AnalysisStore(table_name="t")
    record = store.get("r1")
    assert record.status == "failed"
    assert "boom" in record.error_message

from unittest.mock import AsyncMock, patch

import boto3
import pytest
from config import get_settings
from fastapi.testclient import TestClient
from metrics import ANALYSIS_COUNT, ANALYSIS_DURATION, MCP_TOOL_CALL_COUNT
from moto import mock_aws

from app.health import build_health_app
from app.mcp_clients import call_github_tool
from app.nodes.report_saver import report_saver
from app.runner import run_analysis


def _counter_value(counter, **labels) -> float:
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total") and sample.labels == labels:
                return sample.value
    return 0.0

def _histogram_count(histogram) -> float:
    for metric in histogram.collect():
        for sample in metric.samples:
            if sample.name.endswith("_count"):
                return sample.value
    return 0.0

@pytest.fixture(autouse=True)
def _settings_env(monkeypatch):
    # Same get_settings()-needs-every-field / @lru_cache pattern as test_mcp_clients.py.
    monkeypatch.setenv("DYNAMODB_TABLE", "unused-in-this-test")
    monkeypatch.setenv("S3_BUCKET", "unused-in-this-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused-in-this-test")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github:8100")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "unused-in-this-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

def test_metrics_endpoint_is_exposed_on_the_health_app():
    client = TestClient(build_health_app())
    client.get("/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "testscope_mcp_tool_calls_total" in response.text

@pytest.mark.asyncio
async def test_call_github_tool_increments_mcp_tool_call_count_on_success():
    before = _counter_value(MCP_TOOL_CALL_COUNT, tool="get_repository", status="success")
    async def fake_call_once(base_url, tool_name, kwargs):
        return {"default_branch": "main"}
    with patch("app.mcp_clients._call_once", new=AsyncMock(side_effect=fake_call_once)):
        await call_github_tool("get_repository", owner="acme", repo="widgets")
    after = _counter_value(MCP_TOOL_CALL_COUNT, tool="get_repository", status="success")
    assert after == before + 1

@pytest.mark.asyncio
async def test_call_github_tool_counts_error_status_on_terminal_failure():
    before = _counter_value(MCP_TOOL_CALL_COUNT, tool="get_issue", status="error")
    async def fake_call_once(base_url, tool_name, kwargs):
        raise RuntimeError("404 Not Found")
    with (
        patch("app.mcp_clients._call_once", new=AsyncMock(side_effect=fake_call_once)),
        pytest.raises(RuntimeError, match="404"),
    ):
        await call_github_tool("get_issue", owner="acme", repo="does-not-exist")
    after = _counter_value(MCP_TOOL_CALL_COUNT, tool="get_issue", status="error")
    assert after == before + 1

@pytest.mark.asyncio
async def test_report_saver_increments_analysis_count():
    before = _counter_value(ANALYSIS_COUNT, status="completed")
    state = {"analysis_id": "m1", "repository": "acme/widgets", "issue_number": 1,
              "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "missing_tests": [],
              "test_plan": [], "tool_call_trace": [], "warnings": [], "status": "running"}
    with patch("app.nodes.report_saver.call_test_mcp_tool",
               new=AsyncMock(return_value={"s3_report_key": "k", "dynamodb_status": "saved"})):
        await report_saver(state)
    after = _counter_value(ANALYSIS_COUNT, status="completed")
    assert after == before + 1

@pytest.fixture
def store_env(monkeypatch):
    # Same leak-across-test-files reasoning as test_runner.py's own store_env fixture.
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "metrics-test-table")
    monkeypatch.setenv("S3_BUCKET", "unused")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused")
    monkeypatch.setenv("MCP_GITHUB_URL", "unused")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "unused")
    get_settings.cache_clear()
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="metrics-test-table", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_run_analysis_observes_analysis_duration(store_env):
    before = _histogram_count(ANALYSIS_DURATION)
    with (
        patch("app.runner._graph") as mock_graph,
        patch("app.runner.call_test_mcp_tool", new=AsyncMock(return_value={})),
    ):
        mock_graph.ainvoke = AsyncMock(return_value={
            "analysis_id": "m2", "repository": "acme/widgets", "issue_number": 1,
            "status": "completed", "tool_call_trace": [], "warnings": [], "missing_tests": [],
        })
        await run_analysis(analysis_id="m2", repository="acme/widgets", issue_number=1, notes=None)
    assert _histogram_count(ANALYSIS_DURATION) == before + 1

import os

# Same requirement as test_health.py: server.py instantiates GithubClient() at module
# scope, reading MCP_GITHUB_URL eagerly — must be set before `from server import
# build_health_app` below. Set independently here (not relying on test_health.py having
# already run/imported server first) since running this file in isolation
# (pytest tests/test_metrics.py) proved that dependency real: KeyError otherwise.
os.environ.setdefault("MCP_GITHUB_URL", "http://mcp-github:8100/mcp")
os.environ.setdefault("GITHUB_TOKEN", "test-token")

import pytest
from fastapi.testclient import TestClient

from mcp_metrics import MCP_TOOL_CALL_COUNT, MCP_TOOL_LATENCY, instrument_tool
from server import build_health_app


def _counter_value(counter, **labels) -> float:
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total") and sample.labels == labels:
                return sample.value
    return 0.0

def test_metrics_endpoint_is_exposed_on_the_health_app():
    client = TestClient(build_health_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "testscope_mcp_tool_calls_total" in response.text

def test_instrument_tool_counts_sync_success():
    before = _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_sync_ok", status="success")

    @instrument_tool("unit_test_sync_ok")
    def sync_ok(x: int) -> int:
        return x + 1

    assert sync_ok(1) == 2
    assert _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_sync_ok", status="success") == before + 1

def test_instrument_tool_counts_sync_error():
    before = _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_sync_err", status="error")

    @instrument_tool("unit_test_sync_err")
    def sync_err():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        sync_err()
    assert _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_sync_err", status="error") == before + 1

@pytest.mark.asyncio
async def test_instrument_tool_counts_async_success():
    before = _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_async_ok", status="success")

    @instrument_tool("unit_test_async_ok")
    async def async_ok(x: int) -> int:
        return x + 1

    assert await async_ok(1) == 2
    assert _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_async_ok", status="success") == before + 1

@pytest.mark.asyncio
async def test_instrument_tool_counts_async_error():
    before = _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_async_err", status="error")

    @instrument_tool("unit_test_async_err")
    async def async_err():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await async_err()
    assert _counter_value(MCP_TOOL_CALL_COUNT, tool="unit_test_async_err", status="error") == before + 1

def test_instrument_tool_preserves_original_signature_for_schema_introspection():
    # MCPServer's own @mcp.tool() decorator (applied *outside* @instrument_tool in
    # server.py) needs the original parameter names/types to build each tool's schema —
    # functools.wraps' __wrapped__ must survive so inspect.signature() unwraps correctly.
    import inspect

    @instrument_tool("unit_test_sig")
    def sample(analysis_id: str, path: str) -> dict:
        return {}

    sig = inspect.signature(sample)
    assert list(sig.parameters) == ["analysis_id", "path"]

def test_instrument_tool_observes_latency():
    before = 0.0
    for metric in MCP_TOOL_LATENCY.collect():
        for sample in metric.samples:
            if sample.name.endswith("_count") and sample.labels == {"tool": "unit_test_latency"}:
                before = sample.value

    @instrument_tool("unit_test_latency")
    def sample():
        return "ok"

    sample()
    after = 0.0
    for metric in MCP_TOOL_LATENCY.collect():
        for sample_ in metric.samples:
            if sample_.name.endswith("_count") and sample_.labels == {"tool": "unit_test_latency"}:
                after = sample_.value
    assert after == before + 1

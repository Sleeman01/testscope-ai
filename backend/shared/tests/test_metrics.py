from metrics import (
    ANALYSIS_COUNT,
    ANALYSIS_DURATION,
    API_REQUEST_COUNT,
    API_REQUEST_LATENCY,
    LLM_CALL_COUNT,
    MCP_TOOL_CALL_COUNT,
    MCP_TOOL_LATENCY,
)


def _sample_names(metric) -> set[str]:
    return {sample.name for family in metric.collect() for sample in family.samples}

def test_primitives_accept_their_declared_labels_and_expose_the_documented_metric_names():
    # api/worker's own suites exercise these through real request/tool-call code paths,
    # but backend/shared's own test run never imports metrics.py at all otherwise (same
    # class of gap Task 9's test_config.py closed for config.py). A labeled Counter/
    # Histogram emits no samples from .collect() at all until some label combination has
    # been touched at least once (confirmed empirically — checking sample names before any
    # observation returns an empty set, not the metric's declared-but-unused name) — so
    # this observes each primitive first, then asserts on what it actually emits.
    API_REQUEST_COUNT.labels(method="GET", path="/health/live", status=200).inc()
    API_REQUEST_LATENCY.labels(path="/health/live").observe(0.01)
    ANALYSIS_COUNT.labels(status="completed").inc()
    ANALYSIS_DURATION.observe(1.0)
    LLM_CALL_COUNT.labels(status="success").inc()
    MCP_TOOL_CALL_COUNT.labels(tool="find_test_files", status="success").inc()
    MCP_TOOL_LATENCY.labels(tool="find_test_files").observe(0.5)

    assert "testscope_api_requests_total" in _sample_names(API_REQUEST_COUNT)
    assert "testscope_api_request_duration_seconds_count" in _sample_names(API_REQUEST_LATENCY)
    assert "testscope_analyses_total" in _sample_names(ANALYSIS_COUNT)
    assert "testscope_analysis_duration_seconds_count" in _sample_names(ANALYSIS_DURATION)
    assert "testscope_llm_calls_total" in _sample_names(LLM_CALL_COUNT)
    assert "testscope_mcp_tool_calls_total" in _sample_names(MCP_TOOL_CALL_COUNT)
    assert "testscope_mcp_tool_duration_seconds_count" in _sample_names(MCP_TOOL_LATENCY)

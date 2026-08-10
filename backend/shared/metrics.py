from prometheus_client import Counter, Histogram

API_REQUEST_COUNT = Counter("testscope_api_requests_total", "API requests", ["method", "path", "status"])
API_REQUEST_LATENCY = Histogram("testscope_api_request_duration_seconds", "API request latency", ["path"])

ANALYSIS_COUNT = Counter("testscope_analyses_total", "Analyses run", ["status"])
ANALYSIS_DURATION = Histogram("testscope_analysis_duration_seconds", "Full analysis duration")
LLM_CALL_COUNT = Counter("testscope_llm_calls_total", "LLM calls", ["status"])
MCP_TOOL_CALL_COUNT = Counter("testscope_mcp_tool_calls_total", "MCP tool calls", ["tool", "status"])
MCP_TOOL_LATENCY = Histogram("testscope_mcp_tool_duration_seconds", "MCP tool call latency", ["tool"])

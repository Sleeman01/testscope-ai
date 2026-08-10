import functools
import inspect
import time

from prometheus_client import Counter, Histogram

# mcp-server has no dependency on backend/shared (it's a fully separate process/package,
# confirmed via its own py-modules list) — so unlike api/worker, it declares its own local
# Counter/Histogram instances here rather than importing backend/shared/metrics.py. Same
# metric names as design.md §12/plan.md Task 39 intend though: Prometheus differentiates
# same-named metrics from different services by scrape-target labels (pod/job), not by the
# metric name itself, so this doesn't collide with api/worker's own registries — those are
# separate processes with separate default CollectorRegistrys entirely.
#
# Named mcp_metrics.py, not metrics.py: a first attempt using metrics.py here broke
# backend/api and backend/worker outright — both backend/shared and mcp-server are
# editable-installed as flat py-modules into the same shared .venv, so a bare top-level
# `metrics.py` in both collided exactly like Task 18's app/app collision (Phase 4), except
# this one isn't transient/RED-verification-only: with both modules genuinely present,
# `from metrics import ...` always resolves to whichever finder wins sys.meta_path order
# (mcp-server's, here) — confirmed empirically: api/worker's own test suites failed with
# `ImportError: cannot import name 'API_REQUEST_COUNT' from 'metrics'
# (.../mcp-server/metrics.py)` before this rename.
MCP_TOOL_CALL_COUNT = Counter("testscope_mcp_tool_calls_total", "MCP tool calls", ["tool", "status"])
MCP_TOOL_LATENCY = Histogram("testscope_mcp_tool_duration_seconds", "MCP tool call latency", ["tool"])

def instrument_tool(tool_name: str):
    """Wraps an @mcp.tool()-decorated function (sync or async) with latency/count metrics.
    Apply *under* @mcp.tool() so MCPServer's own signature introspection still sees the
    original function (functools.wraps sets __wrapped__, which inspect.signature follows
    automatically)."""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                status = "success"
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    status = "error"
                    raise
                finally:
                    MCP_TOOL_LATENCY.labels(tool=tool_name).observe(time.time() - start)
                    MCP_TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            status = "success"
            try:
                return func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                MCP_TOOL_LATENCY.labels(tool=tool_name).observe(time.time() - start)
                MCP_TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()
        return sync_wrapper
    return decorator

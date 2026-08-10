import asyncio
import logging
import time
from datetime import UTC, datetime

from config import get_settings
from dynamodb import AnalysisStore
from metrics import ANALYSIS_DURATION
from models import AnalysisRecord

from app.graph import build_graph
from app.mcp_clients import call_test_mcp_tool
from app.nodes.job_intake import job_intake

logger = logging.getLogger(__name__)

_graph = build_graph()

async def run_analysis(analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None:
    store = AnalysisStore(table_name=get_settings().dynamodb_table)
    state = {
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "notes": notes, "tool_call_trace": [], "warnings": [], "status": "pending",
    }
    try:
        state = job_intake(state, store)
    except Exception:
        # design.md §4: "Malformed message → log, ack, skip (no infinite redrive)." Job
        # Intake couldn't even record status=running, so there's nothing meaningful to run
        # the graph against, clean up, or finalize — log and return rather than let this
        # propagate uncaught (main.py's poll loop has nothing wrapping
        # asyncio.run(run_analysis(...)), so an uncaught exception here previously crashed
        # the whole worker process on a single bad job instead of just skipping it).
        logger.exception("job_intake failed for analysis_id=%s; skipping job", analysis_id)
        return
    start_time = time.time()
    try:
        state = await asyncio.wait_for(_graph.ainvoke(state), timeout=600)
    except TimeoutError:
        state["status"] = "failed"
        state["error_message"] = "analysis timed out"
    except Exception as exc:
        logger.exception("Graph execution failed for analysis_id=%s", analysis_id)
        state["status"] = "failed"
        state["error_message"] = str(exc)
    finally:
        ANALYSIS_DURATION.observe(time.time() - start_time)
        try:
            await call_test_mcp_tool("cleanup_workspace", analysis_id=analysis_id)
        except Exception:
            # Best-effort cleanup only — a failed workspace cleanup shouldn't fail the
            # whole finally block or block the final upsert below, just get logged.
            logger.warning("cleanup_workspace failed for analysis_id=%s (non-fatal)", analysis_id, exc_info=True)
        try:
            now = datetime.now(UTC).isoformat()
            store.upsert(AnalysisRecord(
                analysis_id=analysis_id, repository=repository, issue_number=issue_number,
                status=state.get("status", "failed"), created_at=now, updated_at=now,
                requirement_summary=state.get("requirement", {}).get("feature_name"),
                error_message=state.get("error_message"), storage_status=state.get("storage_status"),
                missing_tests_count=len(state.get("missing_tests", [])),
                tool_call_trace=state.get("tool_call_trace", []),
            ))
        except Exception:
            # Same "log, ack, skip" reasoning as job_intake's own handling above — the
            # analysis already ran (or timed out/errored) by this point, so the SQS message
            # should still be ack'd rather than redelivered; a failed final write shouldn't
            # crash the worker or leave the record stuck at status=running forever.
            logger.exception("Final AnalysisRecord upsert failed for analysis_id=%s", analysis_id)

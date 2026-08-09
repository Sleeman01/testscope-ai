import asyncio
from datetime import datetime, timezone
from config import get_settings
from dynamodb import AnalysisStore
from models import AnalysisRecord
from app.nodes.job_intake import job_intake
from app.graph import build_graph
from app.mcp_clients import call_test_mcp_tool

_graph = build_graph()

async def run_analysis(analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None:
    store = AnalysisStore(table_name=get_settings().dynamodb_table)
    state = {
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "notes": notes, "tool_call_trace": [], "warnings": [], "status": "pending",
    }
    state = job_intake(state, store)
    try:
        state = await asyncio.wait_for(_graph.ainvoke(state), timeout=600)
    except asyncio.TimeoutError:
        state["status"] = "failed"
        state["error_message"] = "analysis timed out"
    except Exception as exc:
        state["status"] = "failed"
        state["error_message"] = str(exc)
    finally:
        try:
            await call_test_mcp_tool("cleanup_workspace", analysis_id=analysis_id)
        except Exception:
            pass
        now = datetime.now(timezone.utc).isoformat()
        store.upsert(AnalysisRecord(
            analysis_id=analysis_id, repository=repository, issue_number=issue_number,
            status=state.get("status", "failed"), created_at=now, updated_at=now,
            requirement_summary=state.get("requirement", {}).get("feature_name"),
            error_message=state.get("error_message"), storage_status=state.get("storage_status"),
            missing_tests_count=len(state.get("missing_tests", [])),
            tool_call_trace=state.get("tool_call_trace", []),
        ))

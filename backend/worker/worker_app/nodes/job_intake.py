from datetime import UTC, datetime

from dynamodb import AnalysisStore
from models import AnalysisRecord


def job_intake(state: dict, store: AnalysisStore) -> dict:
    now = datetime.now(UTC).isoformat()
    store.upsert(AnalysisRecord(
        analysis_id=state["analysis_id"], repository=state["repository"],
        issue_number=state["issue_number"], status="running", created_at=now, updated_at=now,
        tool_call_trace=state.get("tool_call_trace", []),
    ))
    state["status"] = "running"
    return state

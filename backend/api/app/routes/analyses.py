import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from config import get_settings
from dynamodb import AnalysisStore
from sqs import JobQueue
from models import AnalysisRecord
from app.schemas import CreateAnalysisRequest, CreateAnalysisResponse

router = APIRouter(prefix="/api/analyses")

def _store() -> AnalysisStore:
    return AnalysisStore(table_name=get_settings().dynamodb_table)

def _queue() -> JobQueue:
    return JobQueue(get_settings().sqs_queue_url)

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=CreateAnalysisResponse)
def create_analysis(payload: CreateAnalysisRequest):
    analysis_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _store().upsert(AnalysisRecord(
        analysis_id=analysis_id, repository=payload.repository, issue_number=payload.issue_number,
        status="pending", created_at=now, updated_at=now,
    ))
    _queue().send_job(analysis_id, payload.repository, payload.issue_number, payload.notes)
    return CreateAnalysisResponse(analysis_id=analysis_id, status="pending")

from fastapi import HTTPException
from app.schemas import AnalysisStatusResponse, AnalysisListResponse

def _to_status_response(record) -> AnalysisStatusResponse:
    return AnalysisStatusResponse(**record.model_dump(exclude={"tool_call_trace", "user_feedback"}))

@router.get("/{analysis_id}", response_model=AnalysisStatusResponse)
def get_analysis(analysis_id: str):
    record = _store().get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _to_status_response(record)

@router.get("", response_model=AnalysisListResponse)
def list_analyses(repository: str | None = None, issue_number: int | None = None,
                   limit: int = 20, cursor: str | None = None):
    if repository and issue_number is not None:
        records = _store().query_by_repo_issue(repository, issue_number)
        return AnalysisListResponse(analyses=[_to_status_response(r) for r in records], next_cursor=None)
    records, next_cursor = _store().list_recent(limit=limit, cursor=cursor)
    return AnalysisListResponse(analyses=[_to_status_response(r) for r in records], next_cursor=next_cursor)

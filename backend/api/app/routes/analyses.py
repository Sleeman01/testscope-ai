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

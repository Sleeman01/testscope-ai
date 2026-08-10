from typing import Literal

from pydantic import BaseModel


class AnalysisRecord(BaseModel):
    analysis_id: str
    repository: str
    issue_number: int
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str
    updated_at: str
    requirement_summary: str | None = None
    coverage_summary: dict | None = None
    missing_tests_count: int = 0
    s3_report_key: str | None = None
    error_message: str | None = None
    storage_status: str | None = None
    tool_call_trace: list[dict] = []
    github_issue_url: str | None = None
    user_feedback: dict | None = None

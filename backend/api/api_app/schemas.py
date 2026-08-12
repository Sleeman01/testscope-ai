from pydantic import BaseModel, field_validator
from repository import normalize_repository


class CreateAnalysisRequest(BaseModel):
    repository: str
    issue_number: int
    notes: str | None = None

    @field_validator("repository")
    @classmethod
    def _normalize_repository(cls, value: str) -> str:
        return normalize_repository(value)

class CreateAnalysisResponse(BaseModel):
    analysis_id: str
    status: str

class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    repository: str
    issue_number: int
    status: str
    created_at: str
    updated_at: str
    requirement_summary: str | None = None
    coverage_summary: dict | None = None
    missing_tests_count: int = 0
    error_message: str | None = None
    storage_status: str | None = None
    github_issue_url: str | None = None

class AnalysisListResponse(BaseModel):
    analyses: list[AnalysisStatusResponse]
    next_cursor: str | None = None

class ReportResponse(BaseModel):
    analysis_id: str
    requirement: dict
    coverage_matrix: list[dict]
    test_plan: list[dict]
    missing_tests: list[dict]
    tool_call_trace: list[dict]
    download_url: str

class GithubIssueResponse(BaseModel):
    github_issue_url: str

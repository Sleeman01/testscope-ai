from typing import TypedDict

class AgentState(TypedDict):
    analysis_id: str
    repository: str
    issue_number: int
    notes: str | None
    default_branch: str
    issue_body: str
    issue_comments: list[str]
    requirement: dict
    search_keywords: list[str]
    candidate_files: list[dict]
    test_metadata: dict
    coverage_matrix: list[dict]
    test_plan: list[dict]
    missing_tests: list[dict]
    warnings: list[str]
    tool_call_trace: list[dict]
    status: str
    error_message: str | None

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
    # Task 17's report_saver sets this (str "saved"/"failed"), but it was missing from
    # Task 10's original AgentState — confirmed by testing that LangGraph's StateGraph
    # silently drops any key a node returns that isn't declared in the TypedDict schema
    # (verified with a minimal reproduction), so runner.py's final AnalysisRecord always
    # got storage_status=None regardless of whether the real save succeeded or failed,
    # defeating design.md §13's "storage_status=failed logged and alerted, not silently
    # dropped" requirement — ironically via the exact silent-drop it warns against.
    storage_status: str | None

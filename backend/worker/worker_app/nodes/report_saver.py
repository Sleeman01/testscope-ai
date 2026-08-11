import logging

from worker_app.mcp_clients import call_test_mcp_tool

logger = logging.getLogger(__name__)


async def report_saver(state: dict) -> dict:
    # ANALYSIS_COUNT is intentionally NOT incremented here (Task 39 originally did, per
    # plan.md's literal snippet — moved in the Task 39 follow-up fix). report_saver only
    # ever runs on the path where every upstream node already succeeded (early failures in
    # request_validator/requirement_retriever/requirement_parser route straight to END via
    # their own conditional edges, per Task 17's graph wiring), so state["status"] here is
    # unconditionally "completed" — incrementing the counter only from this node meant the
    # "failed" label could never fire, even though early-terminated/timed-out/excepted
    # analyses are exactly the outcomes a status-labeled counter needs to distinguish.
    # app/runner.py's finally block is the one place every terminal outcome passes through
    # (it already reads the same state.get("status", "failed") to build the final
    # AnalysisRecord), so that's where the single, correctly-labeled increment now lives.
    state["status"] = "completed"
    try:
        # Real bug, pre-existing since Task 17 — first exposed by Task 43's real end-to-end
        # run (every earlier test mocks this call entirely, or constructs AnalysisRecord
        # fixtures with s3_report_key already set, so the gap in this actual data flow never
        # surfaced): the tool's return value (`{s3_report_key, dynamodb_status}`) was
        # discarded outright. Without capturing s3_report_key into state, runner.py's final
        # AnalysisRecord write has never had a value to put there — GET .../report has been
        # unreachable (`s3_report_key=None` -> a botocore ParamValidationError, 500) for
        # every analysis this project has ever completed, `storage_status: "saved"`
        # notwithstanding.
        result = await call_test_mcp_tool(
            "save_coverage_report", analysis_id=state["analysis_id"], repository=state["repository"],
            issue_number=state["issue_number"], requirement=state["requirement"],
            coverage_matrix=state["coverage_matrix"], missing_tests=state["missing_tests"],
            test_plan=state["test_plan"], status=state["status"], tool_call_trace=state.get("tool_call_trace", []),
        )
        state["s3_report_key"] = result["s3_report_key"]
        state["storage_status"] = "saved"
    except Exception as exc:
        logger.exception("save_coverage_report failed for analysis_id=%s", state["analysis_id"])
        state["storage_status"] = "failed"
        state.setdefault("warnings", []).append(f"Report save failed: {exc}")
    return state

from app.mcp_clients import call_test_mcp_tool

async def report_saver(state: dict) -> dict:
    state["status"] = "completed"
    try:
        await call_test_mcp_tool(
            "save_coverage_report", analysis_id=state["analysis_id"], repository=state["repository"],
            issue_number=state["issue_number"], requirement=state["requirement"],
            coverage_matrix=state["coverage_matrix"], missing_tests=state["missing_tests"],
            test_plan=state["test_plan"], status=state["status"], tool_call_trace=state.get("tool_call_trace", []),
        )
        state["storage_status"] = "saved"
    except Exception as exc:
        state["storage_status"] = "failed"
        state.setdefault("warnings", []).append(f"Report save failed: {exc}")
    return state

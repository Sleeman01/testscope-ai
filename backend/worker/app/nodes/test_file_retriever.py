from app.mcp_clients import call_test_mcp_tool

async def test_file_retriever(state: dict) -> dict:
    try:
        result = await call_test_mcp_tool(
            "find_test_files", analysis_id=state["analysis_id"], repository=state["repository"],
            ref=state["default_branch"], keywords=state["search_keywords"],
        )
        state["candidate_files"] = result["files"]
    except Exception as exc:
        state["candidate_files"] = []
        state.setdefault("warnings", []).append(f"find_test_files failed; continuing with no candidate files: {exc}")
    return state

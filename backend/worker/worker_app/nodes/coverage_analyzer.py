from typing import Literal

from pydantic import BaseModel, RootModel

from worker_app.llm_client import call_llm


class CoverageEntry(BaseModel):
    criterion_id: str
    status: Literal["Covered", "Partially covered", "Not covered", "Unable to determine"]
    evidence: list[str]
    explanation: str

class CoverageMatrix(RootModel[list[CoverageEntry]]):
    pass

SYSTEM_PROMPT = """You are a software quality analysis agent. For each acceptance criterion,
decide whether the provided test metadata demonstrates it is Covered, Partially covered,
Not covered, or Unable to determine. Only cite evidence (file path + test name) that appears
in the provided metadata — never invent file paths or test names. If genuinely ambiguous,
use "Unable to determine" rather than guessing."""

async def coverage_analyzer(state: dict) -> dict:
    criteria = state["requirement"]["acceptance_criteria"]
    metadata_text = "\n".join(f"{path}: {tests}" for path, tests in state["test_metadata"].items()) or "(no test metadata extracted)"
    user_prompt = f"Acceptance criteria:\n{criteria}\n\nTest metadata:\n{metadata_text}"
    result = await call_llm(SYSTEM_PROMPT, user_prompt, CoverageMatrix, tool_name="classify_coverage")
    # call_llm's real return is a CoverageMatrix (RootModel — .root holds the list; it
    # isn't meaningfully iterable on its own, since RootModel inherits BaseModel's
    # field-tuple __iter__). Tests mock call_llm directly with a plain list of
    # CoverageEntry, so accept either shape rather than assuming .root always exists.
    entries = result.root if isinstance(result, CoverageMatrix) else result
    state["coverage_matrix"] = [entry.model_dump() for entry in entries]

    if not state["test_metadata"] and state["candidate_files"]:
        state.setdefault("warnings", []).append(
            "No supported test framework detected; results may be incomplete."
        )
    return state

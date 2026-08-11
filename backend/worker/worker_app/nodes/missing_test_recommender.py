from typing import Literal

from pydantic import BaseModel, RootModel

from worker_app.llm_client import call_llm


class MissingTest(BaseModel):
    behavior: str
    why_it_matters: str
    suggested_type: str
    suggested_priority: Literal["low", "medium", "high"]
    related_criterion_id: str
    risk: str

class MissingTests(RootModel[list[MissingTest]]):
    pass

SYSTEM_PROMPT = """You are a software quality analysis agent. For every criterion marked
Not covered or Partially covered, recommend the missing test(s): what behavior is untested,
why it matters, suggested type/priority, the related criterion id, and the risk of leaving it
untested. Do not recommend tests for criteria already marked Covered."""

async def missing_test_recommender(state: dict) -> dict:
    gaps = [c for c in state["coverage_matrix"] if c["status"] in ("Not covered", "Partially covered")]
    result: MissingTests = await call_llm(SYSTEM_PROMPT, f"Gaps:\n{gaps}", MissingTests, tool_name="recommend_missing_tests")
    state["missing_tests"] = [m.model_dump() for m in result.root]
    return state

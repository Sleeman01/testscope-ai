from typing import Literal
from pydantic import BaseModel, RootModel
from app.llm_client import call_llm

TEST_TYPES = Literal["positive", "negative", "validation", "boundary-value", "permission",
                      "api", "ui", "integration", "error-handling", "regression"]

class TestCase(BaseModel):
    id: str
    title: str
    requirement_id: str
    preconditions: list[str]
    steps: list[str]
    test_data: str
    expected_result: str
    type: TEST_TYPES
    priority: Literal["low", "medium", "high"]
    automation_recommendation: str

class TestPlan(RootModel[list[TestCase]]):
    pass

SYSTEM_PROMPT = """You are a software quality analysis agent. Generate a full test plan covering
positive, negative, validation, boundary-value, permission, API, UI, integration, error-handling,
and regression scenarios for the given requirement. Every test case must reference a real
acceptance criterion id."""

async def test_plan_generator(state: dict) -> dict:
    user_prompt = f"Requirement:\n{state['requirement']}\n\nCurrent coverage:\n{state['coverage_matrix']}"
    result: TestPlan = await call_llm(SYSTEM_PROMPT, user_prompt, TestPlan, tool_name="generate_test_plan")
    state["test_plan"] = [tc.model_dump() for tc in result.root]
    return state

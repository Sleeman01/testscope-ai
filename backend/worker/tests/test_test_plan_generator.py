from unittest.mock import AsyncMock, patch

import pytest

from worker_app.nodes.test_plan_generator import TestCase, TestPlan, test_plan_generator

# The imported node function's name matches pytest's test_* discovery glob — without
# this, pytest tries to collect and run it directly as a test case too (see Task 13's
# test_test_search_planner.py for the same fix). TestCase/TestPlan hit the milder class
# version of the same issue (pytest's default python_classes = Test*): it only warns
# (PytestCollectionWarning: cannot collect ... because it has an __init__ constructor)
# rather than erroring, since pydantic models define __init__, but __test__ = False
# silences it the same way.
test_plan_generator.__test__ = False
TestCase.__test__ = False
TestPlan.__test__ = False

@pytest.mark.asyncio
async def test_generates_scenarios_across_categories():
    state = {"requirement": {"acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}]},
              "coverage_matrix": [], "tool_call_trace": [], "warnings": []}
    stub = TestPlan(root=[TestCase(id="TC1", title="Reject invalid password", requirement_id="AC1",
                                    preconditions=["user exists"], steps=["POST /api/login with wrong password"],
                                    test_data="password=wrong", expected_result="401 response",
                                    type="negative", priority="high", automation_recommendation="automate via pytest")])
    with patch("worker_app.nodes.test_plan_generator.call_llm", new=AsyncMock(return_value=stub)):
        result = await test_plan_generator(state)
    assert result["test_plan"][0]["type"] == "negative"

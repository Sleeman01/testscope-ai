from unittest.mock import AsyncMock, patch

import pytest

from worker_app.nodes.missing_test_recommender import (
    MissingTest,
    MissingTests,
    missing_test_recommender,
)


@pytest.mark.asyncio
async def test_recommends_missing_scenarios_for_gaps():
    state = {"requirement": {"acceptance_criteria": [{"id": "AC1", "text": "x"}]},
              "coverage_matrix": [{"criterion_id": "AC1", "status": "Not covered"}],
              "tool_call_trace": [], "warnings": []}
    stub = MissingTests(root=[MissingTest(behavior="401 on invalid password", why_it_matters="security boundary",
                                           suggested_type="negative", suggested_priority="high",
                                           related_criterion_id="AC1", risk="unauthorized access if unverified")])
    with patch("worker_app.nodes.missing_test_recommender.call_llm", new=AsyncMock(return_value=stub)):
        result = await missing_test_recommender(state)
    assert result["missing_tests"][0]["related_criterion_id"] == "AC1"

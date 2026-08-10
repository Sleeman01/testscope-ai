from unittest.mock import AsyncMock, patch

import pytest

from app.nodes.requirement_parser import (
    AcceptanceCriterion,
    Requirement,
    requirement_parser,
)


@pytest.mark.asyncio
async def test_extracts_structured_requirement():
    state = {"issue_body": "Users must be able to log in with email and password.",
             "issue_comments": [], "tool_call_trace": [], "warnings": []}
    stub_result = Requirement(
        feature_name="Login", business_objective="Let users authenticate",
        functional_requirements=["Email/password login"],
        acceptance_criteria=[AcceptanceCriterion(id="AC1", text="Invalid password returns 401")],
        validation_rules=[], user_roles=["user"], constraints=[], gaps=[],
    )
    with patch("app.nodes.requirement_parser.call_llm", new=AsyncMock(return_value=stub_result)):
        result = await requirement_parser(state)
    assert result["requirement"]["feature_name"] == "Login"
    assert len(result["requirement"]["acceptance_criteria"]) == 1
    assert result.get("status") != "failed"

@pytest.mark.asyncio
async def test_terminates_gracefully_when_no_criteria_found():
    state = {"issue_body": "not much here", "issue_comments": [], "tool_call_trace": [], "warnings": []}
    stub_result = Requirement(
        feature_name="Unknown", business_objective="", functional_requirements=[],
        acceptance_criteria=[], validation_rules=[], user_roles=[], constraints=[],
        gaps=["No acceptance criteria stated in the issue"],
    )
    with patch("app.nodes.requirement_parser.call_llm", new=AsyncMock(return_value=stub_result)):
        result = await requirement_parser(state)
    assert result["status"] == "failed"
    assert "acceptance criteria" in result["error_message"].lower()

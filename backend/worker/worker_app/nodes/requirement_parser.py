from pydantic import BaseModel

from worker_app.llm_client import call_llm


class AcceptanceCriterion(BaseModel):
    id: str
    text: str

class Requirement(BaseModel):
    feature_name: str
    business_objective: str
    functional_requirements: list[str]
    acceptance_criteria: list[AcceptanceCriterion]
    validation_rules: list[str]
    user_roles: list[str]
    constraints: list[str]
    gaps: list[str]

SYSTEM_PROMPT = """You are a software quality analysis agent. Extract structured requirements
from a GitHub issue. Base your output only on the issue text provided — never invent acceptance
criteria, constraints, or roles that are not stated or clearly implied. If information is
missing, list it in `gaps` instead of guessing."""

async def requirement_parser(state: dict) -> dict:
    user_prompt = f"Issue body:\n{state['issue_body']}\n\nComments:\n" + "\n---\n".join(state.get("issue_comments", []))
    requirement: Requirement = await call_llm(SYSTEM_PROMPT, user_prompt, Requirement, tool_name="extract_requirement")
    state["requirement"] = requirement.model_dump()
    if not requirement.acceptance_criteria:
        state["status"] = "failed"
        state["error_message"] = "No acceptance criteria found in issue body or comments"
    return state

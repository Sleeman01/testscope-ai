from pydantic import BaseModel

from app.llm_client import call_llm


class SearchKeywords(BaseModel):
    keywords: list[str]

SYSTEM_PROMPT = """You generate repository search keywords for finding pytest test files
relevant to given acceptance criteria. Prefer concrete function names, endpoint paths,
component names, and domain terms over generic words."""

async def test_search_planner(state: dict) -> dict:
    criteria_text = "\n".join(f"- {c['text']}" for c in state["requirement"]["acceptance_criteria"])
    result: SearchKeywords = await call_llm(SYSTEM_PROMPT, criteria_text, SearchKeywords, tool_name="generate_keywords")
    state["search_keywords"] = result.keywords
    return state

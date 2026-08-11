from anthropic import AsyncAnthropic
from config import get_settings
from metrics import LLM_CALL_COUNT
from pydantic import BaseModel

from retry import with_retry


async def call_llm(system_prompt: str, user_prompt: str, response_model: type[BaseModel], tool_name: str) -> BaseModel:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Real bug, pre-existing since Task 13/16/17 (coverage_analyzer.py, test_plan_generator.py,
    # missing_test_recommender.py all use `RootModel[list[...]]`) — first exposed here because
    # every test through Task 43 mocks call_llm itself, so this function's actual Anthropic
    # request has never run for real before. Anthropic's tool `input_schema` must have
    # `"type": "object"` at the top level; `RootModel[list[X]].model_json_schema()` instead
    # produces `{"type": "array", ...}`, which the API rejects with
    # `tools.0.custom.input_schema.type: Input should be 'object'`. Wrap the array schema in a
    # single-property object for the request, then unwrap on the way back — the three node
    # files and their `.root` usage are untouched, since call_llm's return contract (a
    # validated `response_model` instance) doesn't change.
    schema = response_model.model_json_schema()
    is_array_schema = schema.get("type") == "array"
    input_schema = {"type": "object", "properties": {"entries": schema}, "required": ["entries"]} if is_array_schema else schema

    async def _do_call():
        return await client.messages.create(
            model=settings.anthropic_model,
            # Real bug, found via the same first-real-execution path as the array-schema one
            # above: 4096 was too small for TestPlan's verbose per-test-case output against a
            # real, multi-criterion requirement — confirmed directly (`stop_reason:
            # "max_tokens"`, `usage.output_tokens: 4096`, `tool_use.input` truncated to an
            # empty dict, no "entries" key at all). 16000 matches the documented safe ceiling
            # for a non-streaming request (higher risks the SDK's own HTTP timeout guard).
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[{"name": tool_name, "input_schema": input_schema}],
            tool_choice={"type": "tool", "name": tool_name},
        )

    status = "success"
    try:
        response = await with_retry(_do_call, max_attempts=3, backoff_base=1.0)
    except Exception:
        status = "error"
        raise
    finally:
        LLM_CALL_COUNT.labels(status=status).inc()

    tool_use = next(block for block in response.content if block.type == "tool_use")
    payload = tool_use.input["entries"] if is_array_schema else tool_use.input
    return response_model.model_validate(payload)

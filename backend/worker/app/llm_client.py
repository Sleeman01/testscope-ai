from anthropic import AsyncAnthropic
from config import get_settings
from pydantic import BaseModel

from retry import with_retry


async def call_llm(system_prompt: str, user_prompt: str, response_model: type[BaseModel], tool_name: str) -> BaseModel:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _do_call():
        return await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[{"name": tool_name, "input_schema": response_model.model_json_schema()}],
            tool_choice={"type": "tool", "name": tool_name},
        )

    response = await with_retry(_do_call, max_attempts=3, backoff_base=1.0)
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return response_model.model_validate(tool_use.input)

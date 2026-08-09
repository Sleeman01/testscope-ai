import asyncio
from typing import Any, Callable

def _always_retryable(exc: Exception) -> bool:
    return True

async def with_retry(
    fn, *args,
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    is_retryable: Callable[[Exception], bool] = _always_retryable,
    **kwargs,
) -> Any:
    for attempt in range(max_attempts):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            if not is_retryable(exc) or attempt >= max_attempts - 1:
                raise
            await asyncio.sleep(backoff_base * (2 ** attempt))

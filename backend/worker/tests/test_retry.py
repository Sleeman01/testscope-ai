import pytest
from retry import with_retry

@pytest.mark.asyncio
async def test_succeeds_after_transient_failures():
    calls = {"count": 0}
    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("transient")
        return "ok"
    result = await with_retry(flaky, max_attempts=3, backoff_base=0.01)
    assert result == "ok"
    assert calls["count"] == 3

@pytest.mark.asyncio
async def test_reraises_after_exhausting_attempts():
    async def always_fails():
        raise TimeoutError("still failing")
    with pytest.raises(TimeoutError):
        await with_retry(always_fails, max_attempts=2, backoff_base=0.01)

@pytest.mark.asyncio
async def test_does_not_retry_when_is_retryable_returns_false():
    calls = {"count": 0}
    async def fails_terminally():
        calls["count"] += 1
        raise ValueError("404 Not Found")
    with pytest.raises(ValueError):
        await with_retry(fails_terminally, max_attempts=3, backoff_base=0.01, is_retryable=lambda e: "404" not in str(e))
    assert calls["count"] == 1  # no retry attempted

import asyncio
import random
from typing import Any, Callable, TypeVar

from ..types import RetryConfig

T = TypeVar("T")


def calculate_retry_delay(attempt: int, config: RetryConfig) -> float:
    """计算重试延迟（指数退避 + jitter）"""
    delay = min(config.base_delay * (2 ** attempt), config.max_delay)
    return delay + random.uniform(0, 1)


async def with_retry(
    func: Callable[..., T],
    config: RetryConfig | None = None,
    error_codes: set[str] | None = None,
) -> T:
    """带重试的函数调用"""
    config = config or RetryConfig()
    attempt = 1

    while True:
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            error_code = getattr(e, "code", None)
            if error_code is not None:
                error_code_str = error_code.value if hasattr(error_code, "value") else str(error_code)
            else:
                error_code_str = "unknown"

            is_retryable = error_code_str in config.retryable_codes
            if error_codes and error_code_str in error_codes:
                is_retryable = True

            if not is_retryable or attempt >= config.max_attempts:
                raise

            attempt += 1
            delay = calculate_retry_delay(attempt, config)
            await asyncio.sleep(delay)

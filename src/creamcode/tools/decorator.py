from typing import Callable, TypeVar, ParamSpec, overload
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

_global_registry = None


def set_global_registry(registry) -> None:
    global _global_registry
    _global_registry = registry


def get_global_registry():
    return _global_registry


def tool(
    name: str | None = None,
    description: str | None = None,
):
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await func(*args, **kwargs)

        wrapper._is_tool = True
        wrapper._tool_name = name or func.__name__
        wrapper._tool_description = description or func.__doc__

        if _global_registry is not None:
            from creamcode.types import Tool
            tool_def = Tool(
                name=wrapper._tool_name,
                description=wrapper._tool_description or "",
                parameters={}
            )
            _global_registry.register(tool_def, wrapper)

        return wrapper

    return decorator

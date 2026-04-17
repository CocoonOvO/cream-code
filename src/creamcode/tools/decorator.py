from typing import Callable, TypeVar, ParamSpec, get_type_hints, Any
from functools import wraps
import inspect

P = ParamSpec('P')
R = TypeVar('R')

_global_registry = None


def set_global_registry(registry) -> None:
    global _global_registry
    _global_registry = registry


def get_global_registry():
    return _global_registry


def _extract_parameters(func: Callable) -> dict:
    """Extract JSON Schema parameters from function signature"""
    try:
        hints = get_type_hints(func)
        sig = inspect.signature(func)
        params = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for name, param in sig.parameters.items():
            if name in hints:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                    Any: "any"
                }
                param_type = hints[name]
                json_type = type_map.get(param_type, "any")
                
                params["properties"][name] = {
                    "type": json_type,
                    "description": f"Parameter {name}"
                }
                
                if param.default is inspect.Parameter.empty:
                    params["required"].append(name)
                else:
                    params["properties"][name]["default"] = param.default
        
        return params
    except Exception:
        return {"type": "object", "properties": {}, "required": []}


def tool(
    name: str | None = None,
    description: str | None = None,
):
    """
    Tool decorator
    
    Usage:
    @tool(name="bash", description="Execute shell command")
    async def bash(command: str) -> str:
        ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "")
        parameters = _extract_parameters(func)
        
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await func(*args, **kwargs)
        
        from creamcode.types import Tool
        wrapper._is_tool = True
        wrapper._tool_name = tool_name
        wrapper._tool_description = tool_desc
        wrapper._tool_def = Tool(
            name=tool_name,
            description=tool_desc,
            parameters=parameters
        )
        
        if _global_registry is not None:
            _global_registry.register(wrapper._tool_def, wrapper)
        
        return wrapper
    
    return decorator

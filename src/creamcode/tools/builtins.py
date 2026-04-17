from creamcode.tools.registry import ToolRegistry


def register_builtins(registry: ToolRegistry):
    """
    Register all builtin tools to registry
    
    Args:
        registry: ToolRegistry instance
    """
    from .bash import bash
    from .file import file_read, file_write, file_edit
    from .web import web_fetch, web_search

    registry.register(
        bash._tool_def,
        bash
    )
    registry.register(
        file_read._tool_def,
        file_read
    )
    registry.register(
        file_write._tool_def,
        file_write
    )
    registry.register(
        file_edit._tool_def,
        file_edit
    )
    registry.register(
        web_fetch._tool_def,
        web_fetch
    )
    registry.register(
        web_search._tool_def,
        web_search
    )

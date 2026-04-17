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

    pass

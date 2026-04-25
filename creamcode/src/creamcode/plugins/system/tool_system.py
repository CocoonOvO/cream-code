from __future__ import annotations

from creamcode.core.event_bus import EventBus
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType
from creamcode.tools.registry import ToolRegistry


class ToolSystemPlugin(Plugin):
    """
    系统插件：工具系统
    负责注册内置工具（Bash, File, Web）
    """

    name = "tool-system"
    version = "0.1.0"
    type = PluginType.SYSTEM
    depends_on = []
    description = "Built-in tools: Bash, File, Web"

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._tools_registered = False

    async def on_load(self) -> None:
        """加载时不做任何事，等待启用时注册工具"""
        pass

    def register_commands(self, cli) -> None:
        """不注册任何 CLI 命令"""
        pass

    def register_tools(self, registry: ToolRegistry) -> None:
        """注册内置工具"""
        if self._tools_registered:
            return

        from creamcode.tools.bash import bash
        from creamcode.tools.file import file_read, file_write, file_edit
        from creamcode.tools.web import web_fetch, web_search

        registry.register(bash._tool_def, bash)
        registry.register(file_read._tool_def, file_read)
        registry.register(file_write._tool_def, file_write)
        registry.register(file_edit._tool_def, file_edit)
        registry.register(web_fetch._tool_def, web_fetch)
        registry.register(web_search._tool_def, web_search)

        self._tools_registered = True

    def unregister_tools(self, registry: ToolRegistry) -> None:
        """注销内置工具"""
        if not self._tools_registered:
            return

        registry.unregister("Bash")
        registry.unregister("FileRead")
        registry.unregister("FileWrite")
        registry.unregister("FileEdit")
        registry.unregister("WebFetch")
        registry.unregister("WebSearch")

        self._tools_registered = False

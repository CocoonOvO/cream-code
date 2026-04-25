from __future__ import annotations

from creamcode.core.event_bus import EventBus
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType
from creamcode.agent import BaseAgent, DefaultAgent
from creamcode.tools.registry import ToolRegistry
from creamcode.memory.context import ContextWindowManager


class AgentSystemPlugin(Plugin):
    """
    系统插件：Agent 系统
    负责创建和管理默认 Agent
    """

    name = "agent-system"
    version = "0.1.0"
    type = PluginType.SYSTEM
    depends_on = []
    description = "Default Agent implementation"

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._agent: DefaultAgent | None = None

    async def on_load(self) -> None:
        """加载时不做任何事"""
        pass

    def register_commands(self, cli) -> None:
        """不注册任何 CLI 命令"""
        pass

    def create_agent(
        self,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        context_manager: ContextWindowManager,
    ) -> BaseAgent:
        """
        创建默认 Agent
        
        Args:
            event_bus: EventBus 实例
            tool_registry: ToolRegistry 实例
            context_manager: ContextWindowManager 实例
            
        Returns:
            DefaultAgent 实例
        """
        self._agent = DefaultAgent(
            event_bus=event_bus,
            tool_registry=tool_registry,
            context_manager=context_manager,
        )
        return self._agent

    def get_agent(self) -> DefaultAgent | None:
        """获取已创建的 Agent"""
        return self._agent

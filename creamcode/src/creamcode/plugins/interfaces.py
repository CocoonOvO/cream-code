from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.event_bus import EventBus
    from ..tools.registry import ToolRegistry
    from ..memory.context import ContextWindowManager
    from ..agent import BaseAgent


class ToolPluginInterface(ABC):
    """工具插件接口"""

    @abstractmethod
    def register_tools(self, registry: ToolRegistry) -> None:
        """注册工具到注册表"""
        pass

    @abstractmethod
    def unregister_tools(self, registry: ToolRegistry) -> None:
        """从注册表注销工具"""
        pass


class MemoryPluginInterface(ABC):
    """记忆插件接口"""

    @abstractmethod
    def create_context_manager(
        self,
        event_bus: EventBus,
        config: dict | None = None,
    ) -> ContextWindowManager:
        """创建上下文管理器"""
        pass


class AgentPluginInterface(ABC):
    """Agent 插件接口"""

    @abstractmethod
    def create_agent(
        self,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        context_manager: ContextWindowManager,
    ) -> BaseAgent:
        """创建 Agent 实例"""
        pass


class AdapterPluginInterface(ABC):
    """适配器插件接口"""

    @abstractmethod
    def get_adapter_class(self):
        """获取适配器类"""
        pass

    @abstractmethod
    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        pass

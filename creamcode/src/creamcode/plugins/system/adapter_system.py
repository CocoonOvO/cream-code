from __future__ import annotations

from creamcode.core.event_bus import EventBus
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType
from creamcode.adapters.registry import AdapterRegistry
from creamcode.adapters.base import BaseAdapter


class AdapterSystemPlugin(Plugin):
    """
    系统插件：适配器系统
    负责注册内置适配器（Anthropic, OpenAI, Ollama, MiniMax）
    """

    name = "adapter-system"
    version = "0.1.0"
    type = PluginType.SYSTEM
    depends_on = []
    description = "Built-in adapters: Anthropic, OpenAI, Ollama, MiniMax"

    def __init__(self, event_bus=None):
        super().__init__(event_bus)
        self._registry: AdapterRegistry | None = None

    async def on_load(self) -> None:
        """加载时不做任何事"""
        pass

    def register_commands(self, cli) -> None:
        """不注册任何 CLI 命令"""
        pass

    def register_adapters(self, registry: AdapterRegistry) -> None:
        """
        注册内置适配器到注册表
        
        Args:
            registry: AdapterRegistry 实例
        """
        if self._registry is not None:
            return

        from creamcode.adapters.anthropic import AnthropicAdapter
        from creamcode.adapters.openai import OpenAIAdapter
        from creamcode.adapters.ollama import OllamaAdapter
        from creamcode.adapters.minimax import MiniMaxAdapter

        registry.register(AnthropicAdapter)
        registry.register(OpenAIAdapter)
        registry.register(OllamaAdapter)
        registry.register(MiniMaxAdapter)

        self._registry = registry

    def unregister_adapters(self, registry: AdapterRegistry) -> None:
        """注销内置适配器"""
        if self._registry is None:
            return

        for adapter_name in ["AnthropicAdapter", "OpenAIAdapter", "OllamaAdapter", "MiniMaxAdapter"]:
            if adapter_name in registry._adapters:
                del registry._adapters[adapter_name]

        self._registry = None

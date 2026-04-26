from __future__ import annotations

from pathlib import Path
from typing import Any

from creamcode.core.event_bus import EventBus
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType
from creamcode.memory.working import WorkingMemory
from creamcode.memory.short_term import ShortTermMemory
from creamcode.memory.long_term import LongTermMemory
from creamcode.memory.context import ContextWindowManager


class MemorySystemPlugin(Plugin):
    """
    系统插件：记忆系统
    负责管理三级记忆和上下文管理
    """

    name = "memory-system"
    version = "0.1.0"
    type = PluginType.SYSTEM
    depends_on = []
    description = "Three-level memory system: Working, ShortTerm, LongTerm"

    def __init__(self, event_bus=None):
        super().__init__(event_bus)
        self._context_manager: ContextWindowManager | None = None
        self._config: dict[str, Any] = {}

    async def on_load(self) -> None:
        """加载时不做任何事"""
        pass

    def register_commands(self, cli) -> None:
        """不注册任何 CLI 命令"""
        pass

    def create_context_manager(
        self,
        event_bus: EventBus,
        config: dict[str, Any] | None = None,
    ) -> ContextWindowManager:
        """
        创建上下文管理器
        
        Args:
            event_bus: EventBus 实例
            config: 配置字典
            
        Returns:
            ContextWindowManager 实例
        """
        if config:
            self._config = config
        else:
            self._config = {}

        storage_dir = Path(self._config.get("storage_dir", "~/.cache/creamcode"))
        storage_dir = storage_dir.expanduser()

        working_memory = WorkingMemory(
            max_tokens=self._config.get("max_tokens", 100000),
            reserved_tokens=self._config.get("reserved_tokens", 4096),
        )

        short_term_memory = ShortTermMemory(
            storage_dir=storage_dir / "short_term",
            max_summaries=self._config.get("max_summaries", 10),
        )

        long_term_memory = LongTermMemory(
            storage_dir=storage_dir / "long_term",
        )

        self._context_manager = ContextWindowManager(
            working_memory=working_memory,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            event_bus=event_bus,
        )

        return self._context_manager

    def get_context_manager(self) -> ContextWindowManager | None:
        """获取已创建的上下文管理器"""
        return self._context_manager

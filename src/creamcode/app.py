from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .core.event_bus import EventBus
from .core.cli_framework import CLIRegistry, CLIApp, InteractiveMode
from .core.plugin_manager import PluginManager, Plugin
from .core.lifecycle import LifecycleManager, LifecycleState
from .tools.registry import ToolRegistry
from .tools.builtins import register_builtins
from .memory.working import WorkingMemory
from .memory.short_term import ShortTermMemory
from .memory.long_term import LongTermMemory
from .memory.context import ContextWindowManager
from .adapters.registry import AdapterRegistry
from .agent import DefaultAgent
from .types import Event


class Application:
    """
    creamcode 应用主类
    
    负责初始化和协调所有子系统:
    - EventBus: 事件通信核心
    - ToolRegistry: 工具注册表
    - CLIRegistry: CLI 命令注册
    - PluginManager: 插件管理
    - Memory System: 三级记忆系统
    - AdapterRegistry: AI 适配器管理
    """

    VERSION = "0.1.0"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._logger = logging.getLogger("creamcode.app")
        
        self.event_bus: EventBus | None = None
        self.cli_registry: CLIRegistry | None = None
        self.plugin_manager: PluginManager | None = None
        self.tool_registry: ToolRegistry | None = None
        self.lifecycle: LifecycleManager | None = None
        self.adapter_registry: AdapterRegistry | None = None
        self.agent: DefaultAgent | None = None
        
        self.working_memory: WorkingMemory | None = None
        self.short_term_memory: ShortTermMemory | None = None
        self.long_term_memory: LongTermMemory | None = None
        self.context_manager: ContextWindowManager | None = None
        
        self._initialized = False

    async def initialize(self) -> None:
        """
        初始化所有子系统
        """
        if self._initialized:
            self._logger.warning("Application already initialized")
            return
        
        self._logger.info("Initializing creamcode application...")
        
        self.event_bus = EventBus()
        self.cli_registry = CLIRegistry()
        self.tool_registry = ToolRegistry(self.event_bus)
        self.lifecycle = LifecycleManager()
        
        await self.event_bus.subscribe("command.registered", self._on_command_registered)
        await self.event_bus.subscribe("plugin.commands_registering", self._on_plugin_commands_registering)
        
        self.plugin_manager = PluginManager(self.event_bus)
        
        self.adapter_registry = AdapterRegistry(self.event_bus)
        
        await self._setup_memory()
        
        self.agent = DefaultAgent(
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            context_manager=self.context_manager,
        )
        
        register_builtins(self.tool_registry)
        
        await self._load_plugins()
        
        await self.lifecycle.on_startup()
        
        self._initialized = True
        self._logger.info("creamcode application initialized successfully")

    async def _on_command_registered(self, event: Event) -> None:
        """Handle command registration events from plugins"""
        self._logger.debug(
            f"Command registered via event: {event.data.get('namespace')}/{event.data.get('name')}"
        )

    async def _on_plugin_commands_registering(self, event: Event) -> None:
        """Handle plugin commands registration event - actually register commands to CLI"""
        plugin = event.data.get("plugin")
        if plugin and self.cli_registry:
            plugin.register_commands(self.cli_registry)

    async def _setup_memory(self) -> None:
        """Initialize memory system"""
        self.working_memory = WorkingMemory(
            max_tokens=self.config.get("max_tokens", 100000),
            reserved_tokens=self.config.get("reserved_tokens", 4096),
        )
        
        storage_dir = Path(self.config.get("storage_dir", "~/.cache/creamcode"))
        storage_dir = storage_dir.expanduser()
        
        self.short_term_memory = ShortTermMemory(
            storage_dir=storage_dir / "short_term",
            max_summaries=self.config.get("max_summaries", 10),
        )
        
        self.long_term_memory = LongTermMemory(
            storage_dir=storage_dir / "long_term",
            event_bus=self.event_bus,
        )
        
        self.context_manager = ContextWindowManager(
            working_memory=self.working_memory,
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            event_bus=self.event_bus,
        )

    async def _load_plugins(self) -> None:
        """Load plugins from configured directories"""
        plugin_dirs = self.config.get("plugin_dirs", [])
        
        for plugin_dir in plugin_dirs:
            plugin_path = Path(plugin_dir).expanduser()
            if plugin_path.exists():
                try:
                    await self.plugin_manager.load_plugin(plugin_path)
                except Exception as e:
                    self._logger.error(f"Failed to load plugin from {plugin_path}: {e}")

    async def run_interactive(self) -> None:
        """Run in interactive mode"""
        if not self._initialized:
            await self.initialize()
        
        cli_app = CLIApp(self.cli_registry)
        interactive = InteractiveMode(cli_app)
        
        self._logger.info("Starting interactive mode...")
        await interactive.run()

    async def run_command(self, command: str, args: dict[str, Any]) -> int:
        """Run a single command"""
        if not self._initialized:
            await self.initialize()
        
        cli_app = CLIApp(self.cli_registry)
        return cli_app.run([command])

    async def shutdown(self) -> None:
        """Shutdown application gracefully"""
        self._logger.info("Shutting down creamcode application...")
        
        if self.lifecycle:
            await self.lifecycle.on_shutdown()
        
        if self.plugin_manager:
            for plugin_name in list(self.plugin_manager.list_plugins()):
                try:
                    await self.plugin_manager.unload_plugin(plugin_name)
                except Exception as e:
                    self._logger.error(f"Failed to unload plugin {plugin_name}: {e}")
        
        self._initialized = False
        self._logger.info("creamcode application shutdown complete")

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def state(self) -> LifecycleState:
        if self.lifecycle:
            return self.lifecycle.get_state()
        return LifecycleState.STOPPED

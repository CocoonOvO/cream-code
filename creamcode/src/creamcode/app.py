from __future__ import annotations

import asyncio
import logging
import importlib
from pathlib import Path
from typing import Any

from .core.event_bus import EventBus
from .core.cli_framework import CLIRegistry, CLIApp, InteractiveMode
from .core.plugin_manager import PluginManager, Plugin
from .core.lifecycle import LifecycleManager, LifecycleState
from .tools.registry import ToolRegistry
from .memory.context import ContextWindowManager
from .adapters.registry import AdapterRegistry
from .types import Event, PluginType


class Application:
    """
    creamcode 应用主类

    负责初始化和协调所有子系统:
    - EventBus: 事件通信核心
    - PluginManager: 插件管理
    - ToolRegistry: 工具注册表 (通过 ToolSystemPlugin)
    - Memory System: 三级记忆系统 (通过 MemorySystemPlugin)
    - AdapterRegistry: AI 适配器管理 (通过 AdapterSystemPlugin)
    - Agent: Agent (通过 AgentSystemPlugin)
    """

    VERSION = "0.1.0"

    SYSTEM_PLUGINS = [
        "creamcode.plugins.system.adapter_system",
        "creamcode.plugins.system.tool_system",
        "creamcode.plugins.system.memory_system",
        "creamcode.plugins.system.agent_system",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._logger = logging.getLogger("creamcode.app")

        self.event_bus: EventBus | None = None
        self.cli_registry: CLIRegistry | None = None
        self.plugin_manager: PluginManager | None = None
        self.tool_registry: ToolRegistry | None = None
        self.lifecycle: LifecycleManager | None = None
        self.adapter_registry: AdapterRegistry | None = None
        self.context_manager: ContextWindowManager | None = None
        self.agent = None

        self._system_plugins: dict[str, Plugin] = {}
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
        self.adapter_registry = AdapterRegistry(self.event_bus)

        await self.event_bus.subscribe("command.registered", self._on_command_registered)
        await self.event_bus.subscribe("plugin.commands_registering", self._on_plugin_commands_registering)

        self.plugin_manager = PluginManager(self.event_bus)

        await self._load_system_plugins()

        await self._load_user_plugins()

        await self.lifecycle.on_startup()

        self._initialized = True
        self._logger.info("creamcode application initialized successfully")

    async def _load_system_plugins(self) -> None:
        """加载系统插件"""
        for plugin_module_name in self.SYSTEM_PLUGINS:
            try:
                module = importlib.import_module(plugin_module_name)

                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                        if getattr(attr, 'type', None) == PluginType.SYSTEM:
                            plugin_class = attr
                            break

                if plugin_class is None:
                    self._logger.warning(f"No SYSTEM plugin found in {plugin_module_name}")
                    continue

                plugin_instance = plugin_class(self.event_bus)
                await plugin_instance.on_load()
                await plugin_instance.on_enable()
                self._system_plugins[plugin_instance.name] = plugin_instance

                self._logger.info(f"Loaded system plugin: {plugin_instance.name}")

            except Exception as e:
                self._logger.error(f"Failed to load system plugin {plugin_module_name}: {e}")

        await self._initialize_components()

    async def _initialize_components(self) -> None:
        """通过插件初始化各个组件"""

        if "tool-system" in self._system_plugins:
            tool_plugin = self._system_plugins["tool-system"]
            if hasattr(tool_plugin, 'register_tools'):
                tool_plugin.register_tools(self.tool_registry)
                self._logger.info("Tools registered from plugin")

        if "adapter-system" in self._system_plugins:
            adapter_plugin = self._system_plugins["adapter-system"]
            if hasattr(adapter_plugin, 'register_adapters'):
                adapter_plugin.register_adapters(self.adapter_registry)
                self._logger.info("Adapters registered from plugin")

        if "memory-system" in self._system_plugins:
            memory_plugin = self._system_plugins["memory-system"]
            if hasattr(memory_plugin, 'create_context_manager'):
                self.context_manager = memory_plugin.create_context_manager(
                    self.event_bus,
                    self.config
                )
                self._logger.info("Memory system initialized from plugin")

        if "agent-system" in self._system_plugins and self.context_manager:
            agent_plugin = self._system_plugins["agent-system"]
            if hasattr(agent_plugin, 'create_agent'):
                self.agent = agent_plugin.create_agent(
                    self.event_bus,
                    self.tool_registry,
                    self.context_manager,
                )
                self._logger.info("Agent created from plugin")

    async def _load_user_plugins(self) -> None:
        """加载用户插件"""
        plugin_dirs = self.config.get("plugin_dirs", [])

        if not plugin_dirs:
            default_user_dir = Path("~/.creamcode/plugins").expanduser()
            if default_user_dir.exists():
                plugin_dirs = [str(default_user_dir)]

        for plugin_dir in plugin_dirs:
            plugin_path = Path(plugin_dir).expanduser()
            if plugin_path.exists() and plugin_path.is_dir():
                for plugin_file in plugin_path.glob("*.py"):
                    if plugin_file.stem.startswith("_"):
                        continue
                    try:
                        await self.plugin_manager.load_plugin(plugin_file)
                    except Exception as e:
                        self._logger.error(f"Failed to load plugin from {plugin_file}: {e}")

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

    def get_system_plugin(self, name: str) -> Plugin | None:
        """获取系统插件"""
        return self._system_plugins.get(name)

    def get_tool_plugin(self):
        """获取工具系统插件"""
        return self._system_plugins.get("tool-system")

    def get_memory_plugin(self):
        """获取记忆系统插件"""
        return self._system_plugins.get("memory-system")

    def get_agent_plugin(self):
        """获取 Agent 系统插件"""
        return self._system_plugins.get("agent-system")

    def get_adapter_plugin(self):
        """获取适配器系统插件"""
        return self._system_plugins.get("adapter-system")

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

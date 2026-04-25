from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Self

import importlib.util
import logging

from ..types import PluginType, PluginMetadata
from .event_bus import EventBus, Event

if TYPE_CHECKING:
    from .cli_framework import CLIRegistry


class PluginLoadError(Exception):
    """插件加载失败"""
    pass


class PluginDependencyError(Exception):
    """插件依赖未满足"""
    pass


class Plugin(ABC):
    """插件基类"""

    name: str = ""
    version: str = "0.1.0"
    type: PluginType = PluginType.USER
    depends_on: list[str] = []
    description: str = ""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def on_load(self):
        """插件加载时调用"""
        pass

    async def on_enable(self):
        """插件启用时调用"""
        self._enabled = True

    async def on_disable(self):
        """插件禁用时调用"""
        self._enabled = False

    async def on_unload(self):
        """插件卸载时调用"""
        pass

    def register_commands(self, cli: 'CLIRegistry'):
        """注册 CLI 命令"""
        pass


class PluginManager:
    """
    插件管理器
    负责插件的加载、卸载、启用、禁用、热重载
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._plugins: dict[str, Plugin] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._states: dict[str, str] = {}
        self._plugin_paths: dict[str, Path] = {}
        self._logger = logging.getLogger("creamcode.plugin_manager")

    async def load_plugin(self, plugin_path: Path) -> Plugin:
        """
        加载插件
        1. 读取插件元数据
        2. 检查依赖
        3. 实例化插件
        4. 调用 on_load
        """
        spec = importlib.util.spec_from_file_location("plugin_module", plugin_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot load plugin from {plugin_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                plugin_class = attr
                break

        if plugin_class is None:
            raise PluginLoadError(f"No Plugin class found in {plugin_path}")

        plugin_instance = plugin_class(self.event_bus)
        metadata = PluginMetadata(
            name=plugin_class.name,
            version=plugin_class.version,
            type=plugin_class.type,
            depends_on=plugin_class.depends_on,
            description=plugin_class.description,
        )

        if not self._check_dependencies(metadata):
            raise PluginDependencyError(f"Dependencies not satisfied for {metadata.name}")

        self._plugins[metadata.name] = plugin_instance
        self._metadata[metadata.name] = metadata
        self._states[metadata.name] = "loaded"
        self._plugin_paths[metadata.name] = plugin_path

        await plugin_instance.on_load()
        await self.event_bus.publish(Event(
            name="plugin.loaded",
            source="plugin_manager",
            data={"name": metadata.name, "version": metadata.version}
        ))

        self._logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")
        return plugin_instance

    async def unload_plugin(self, name: str) -> None:
        """
        卸载插件
        1. 调用 on_unload
        2. 注销 CLI 命令
        3. 删除插件实例
        """
        if name not in self._plugins:
            return

        plugin = self._plugins[name]

        if self._states.get(name) == "enabled":
            await self.disable_plugin(name)

        await plugin.on_unload()

        await self.event_bus.publish(Event(
            name="plugin.commands_unregistered",
            source="plugin_manager",
            data={"name": name}
        ))

        del self._plugins[name]
        del self._metadata[name]
        del self._states[name]
        self._plugin_paths.pop(name, None)

        await self.event_bus.publish(Event(
            name="plugin.unloaded",
            source="plugin_manager",
            data={"name": name}
        ))

        self._logger.info(f"Unloaded plugin: {name}")

    async def enable_plugin(self, name: str) -> None:
        """启用插件"""
        if name not in self._plugins:
            raise PluginLoadError(f"Plugin {name} not loaded")

        plugin = self._plugins[name]
        metadata = self._metadata[name]

        if self._states.get(name) == "enabled":
            return

        if not self._check_dependencies(metadata):
            raise PluginDependencyError(f"Dependencies not satisfied for {name}")

        await self.event_bus.publish(Event(
            name="plugin.commands_registering",
            source="plugin_manager",
            data={"name": name, "plugin": plugin}
        ))
        
        await plugin.on_enable()
        self._states[name] = "enabled"

        await self.event_bus.publish(Event(
            name="plugin.enabled",
            source="plugin_manager",
            data={"name": name}
        ))

        self._logger.info(f"Enabled plugin: {name}")

    async def disable_plugin(self, name: str) -> None:
        """禁用插件"""
        if name not in self._plugins:
            return

        plugin = self._plugins[name]

        if self._states.get(name) != "enabled":
            return

        await self.event_bus.publish(Event(
            name="plugin.commands_unregistering",
            source="plugin_manager",
            data={"name": name}
        ))
        await plugin.on_disable()
        self._states[name] = "disabled"

        await self.event_bus.publish(Event(
            name="plugin.disabled",
            source="plugin_manager",
            data={"name": name}
        ))

        self._logger.info(f"Disabled plugin: {name}")

    async def reload_plugin(self, name: str) -> None:
        """重载插件"""
        if name not in self._plugins:
            raise PluginLoadError(f"Plugin {name} not loaded")

        old_state = self._states.get(name, "loaded")
        plugin_path = self._plugin_paths.get(name)

        if plugin_path is None:
            raise PluginLoadError(f"Cannot find plugin file for {name}")

        await self.unload_plugin(name)
        await self.load_plugin(plugin_path)

        if old_state == "enabled":
            await self.enable_plugin(name)

        self._logger.info(f"Reloaded plugin: {name}")

    def get_plugin(self, name: str) -> Plugin | None:
        """获取插件实例"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginMetadata]:
        """列出所有已加载插件的元数据"""
        return list(self._metadata.values())

    def get_plugin_state(self, name: str) -> str:
        """获取插件状态：loaded, enabled, disabled, error"""
        return self._states.get(name, "error")

    async def load_plugins_from_dir(self, plugin_dir: Path) -> int:
        """
        从目录加载所有插件
        返回加载成功的数量
        """
        if not plugin_dir.exists():
            return 0

        plugin_files = list(plugin_dir.glob("*.py"))
        plugin_metadata = [
            (f, self._extract_metadata_from_file(f)) for f in plugin_files if f.stem != "__init__"
        ]
        sorted_plugins = self._topological_sort([m for _, m in plugin_metadata])

        loaded_count = 0
        errors = []

        for plugin_file, metadata in plugin_metadata:
            if metadata.name in self._plugins:
                continue

            if metadata not in sorted_plugins:
                continue

            try:
                await self.load_plugin(plugin_file)
                loaded_count += 1
            except (PluginLoadError, PluginDependencyError) as e:
                self._states[metadata.name] = "error"
                errors.append((metadata.name, str(e)))
                await self.event_bus.publish(Event(
                    name="plugin.error",
                    source="plugin_manager",
                    data={"name": metadata.name, "error": str(e)}
                ))

        return loaded_count

    def _check_dependencies(self, metadata: PluginMetadata) -> bool:
        """检查依赖是否满足"""
        for dep in metadata.depends_on:
            if dep not in self._plugins:
                return False
            if self._states.get(dep) not in ("loaded", "enabled"):
                return False
        return True

    def _topological_sort(self, plugins: list[PluginMetadata]) -> list[PluginMetadata]:
        """拓扑排序，按依赖顺序返回"""
        result = []
        visited = set()
        visiting = set()

        def visit(plugin: PluginMetadata):
            if plugin.name in visited:
                return
            if plugin.name in visiting:
                return

            visiting.add(plugin.name)

            for dep in plugin.depends_on:
                dep_meta = next((p for p in plugins if p.name == dep), None)
                if dep_meta:
                    visit(dep_meta)

            visiting.remove(plugin.name)
            visited.add(plugin.name)
            result.append(plugin)

        for plugin in plugins:
            visit(plugin)

        return result

    def _extract_metadata_from_file(self, plugin_path: Path) -> PluginMetadata:
        """从插件文件提取元数据"""
        spec = importlib.util.spec_from_file_location("plugin_module", plugin_path)
        if spec is None or spec.loader is None:
            return PluginMetadata(
                name=plugin_path.stem,
                version="0.0.0",
                type=PluginType.USER,
                depends_on=[],
            )

        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                    return PluginMetadata(
                        name=attr.name or plugin_path.stem,
                        version=attr.version or "0.0.0",
                        type=attr.type or PluginType.USER,
                        depends_on=attr.depends_on or [],
                        description=attr.description or "",
                    )
        except Exception:
            pass

        return PluginMetadata(
            name=plugin_path.stem,
            version="0.0.0",
            type=PluginType.USER,
            depends_on=[],
        )

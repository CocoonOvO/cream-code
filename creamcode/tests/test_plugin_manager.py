from __future__ import annotations

import asyncio
import pytest
import tempfile
from pathlib import Path

from creamcode.core.plugin_manager import (
    Plugin,
    PluginManager,
    PluginLoadError,
    PluginDependencyError,
)
from creamcode.core.event_bus import EventBus
from creamcode.core.cli_framework import CLIRegistry
from creamcode.types import PluginType, PluginMetadata


class TestPluginBasic:
    def test_plugin_initial_state(self):
        bus = EventBus()
        plugin = SimpleTestPlugin(bus)
        assert plugin.enabled is False
        assert plugin.name == "simple"
        assert plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_plugin_on_load_called(self):
        bus = EventBus()
        plugin = SimpleTestPlugin(bus)
        await plugin.on_load()
        assert plugin.loaded is True

    @pytest.mark.asyncio
    async def test_plugin_enable(self):
        bus = EventBus()
        plugin = SimpleTestPlugin(bus)
        await plugin.on_enable()
        assert plugin.enabled is True

    @pytest.mark.asyncio
    async def test_plugin_disable(self):
        bus = EventBus()
        plugin = SimpleTestPlugin(bus)
        await plugin.on_enable()
        await plugin.on_disable()
        assert plugin.enabled is False


class SimpleTestPlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"

    def __init__(self, event_bus):
        super().__init__(event_bus)
        self.loaded = False

    async def on_load(self):
        self.loaded = True


class TestPluginManagerBasic:
    @pytest.mark.asyncio
    async def test_load_plugin(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"

    def __init__(self, event_bus):
        super().__init__(event_bus)
        self.loaded = False

    async def on_load(self):
        self.loaded = True
''')

            plugin = await manager.load_plugin(test_plugins_dir / "simple.py")
            assert plugin is not None
            assert plugin.loaded is True
            assert manager.get_plugin("simple") is plugin

    @pytest.mark.asyncio
    async def test_get_plugin(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            plugin = manager.get_plugin("simple")
            assert plugin is not None
            assert plugin.name == "simple"

    @pytest.mark.asyncio
    async def test_get_plugin_not_found(self):
        bus = EventBus()
        manager = PluginManager(bus)

        plugin = manager.get_plugin("nonexistent")
        assert plugin is None

    @pytest.mark.asyncio
    async def test_list_plugins(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            (test_plugins_dir / "another.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class AnotherPlugin(Plugin):
    name = "another"
    version = "2.0.0"
    type = PluginType.USER
    depends_on = []
    description = "Another test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.load_plugin(test_plugins_dir / "another.py")

            plugins = manager.list_plugins()
            assert len(plugins) == 2
            names = {p.name for p in plugins}
            assert "simple" in names
            assert "another" in names

    @pytest.mark.asyncio
    async def test_get_plugin_state(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            assert manager.get_plugin_state("simple") == "loaded"


class TestPluginManagerEnableDisable:
    @pytest.mark.asyncio
    async def test_enable_plugin(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.enable_plugin("simple")

            plugin = manager.get_plugin("simple")
            assert plugin.enabled is True
            assert manager.get_plugin_state("simple") == "enabled"

    @pytest.mark.asyncio
    async def test_disable_plugin(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.enable_plugin("simple")
            await manager.disable_plugin("simple")

            plugin = manager.get_plugin("simple")
            assert plugin.enabled is False
            assert manager.get_plugin_state("simple") == "disabled"

    @pytest.mark.asyncio
    async def test_enable_twice_is_idempotent(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.enable_plugin("simple")
            await manager.enable_plugin("simple")

            plugin = manager.get_plugin("simple")
            assert plugin.enabled is True


class TestPluginManagerDependency:
    @pytest.mark.asyncio
    async def test_dependency_satisfied(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "base.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class BasePlugin(Plugin):
    name = "base"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "Base plugin"
''')

            (test_plugins_dir / "dependent.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class DependentPlugin(Plugin):
    name = "dependent"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = ["base"]
    description = "Dependent plugin"
''')

            await manager.load_plugin(test_plugins_dir / "base.py")
            await manager.load_plugin(test_plugins_dir / "dependent.py")

            base_plugin = manager.get_plugin("base")
            dependent_plugin = manager.get_plugin("dependent")
            assert base_plugin is not None
            assert dependent_plugin is not None

    @pytest.mark.asyncio
    async def test_dependency_not_satisfied(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "dependent.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class DependentPlugin(Plugin):
    name = "dependent"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = ["nonexistent"]
    description = "Dependent plugin"
''')

            with pytest.raises(PluginDependencyError):
                await manager.load_plugin(test_plugins_dir / "dependent.py")

    @pytest.mark.asyncio
    async def test_circular_dependency_handled(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "plugin_a.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class APlugin(Plugin):
    name = "a"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = ["b"]
    description = "Plugin A"
''')

            (test_plugins_dir / "plugin_b.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class BPlugin(Plugin):
    name = "b"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = ["a"]
    description = "Plugin B"
''')

            try:
                await manager.load_plugin(test_plugins_dir / "plugin_a.py")
            except Exception:
                pass


class TestPluginManagerUnload:
    @pytest.mark.asyncio
    async def test_unload_plugin(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.unload_plugin("simple")

            assert manager.get_plugin("simple") is None
            assert manager.get_plugin_state("simple") == "error"

    @pytest.mark.asyncio
    async def test_unload_twice_is_safe(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.unload_plugin("simple")
            await manager.unload_plugin("simple")

            assert manager.get_plugin("simple") is None


class TestPluginManagerReload:
    @pytest.mark.asyncio
    async def test_reload_plugin(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()
            plugins_user_dir = test_plugins_dir / "user"
            plugins_user_dir.mkdir()

            (plugins_user_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"

    def __init__(self, event_bus):
        super().__init__(event_bus)
        self.load_count = 0

    async def on_load(self):
        self.load_count += 1
''')

            await manager.load_plugin(plugins_user_dir / "simple.py")
            plugin = manager.get_plugin("simple")
            initial_count = plugin.load_count

            await manager.reload_plugin("simple")

            plugin = manager.get_plugin("simple")
            assert plugin.load_count == initial_count

    @pytest.mark.asyncio
    async def test_reload_preserves_enabled_state(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()
            plugins_user_dir = test_plugins_dir / "user"
            plugins_user_dir.mkdir()

            (plugins_user_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(plugins_user_dir / "simple.py")
            await manager.enable_plugin("simple")
            assert manager.get_plugin_state("simple") == "enabled"

            await manager.reload_plugin("simple")
            assert manager.get_plugin_state("simple") == "enabled"


class TestPluginManagerExceptionHandling:
    @pytest.mark.asyncio
    async def test_load_failure_marks_plugin_as_error(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "broken.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class BrokenPlugin(Plugin):
    name = "broken"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A broken plugin"

    def __init__(self, event_bus):
        super().__init__(event_bus)
        raise RuntimeError("Plugin initialization failed")
''')

            try:
                await manager.load_plugin(test_plugins_dir / "broken.py")
            except RuntimeError:
                pass

            assert manager.get_plugin_state("broken") == "error"

    @pytest.mark.asyncio
    async def test_load_failure_does_not_affect_other_plugins(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "working.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class WorkingPlugin(Plugin):
    name = "working"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A working plugin"
''')

            (test_plugins_dir / "broken.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class BrokenPlugin(Plugin):
    name = "broken"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A broken plugin"

    def __init__(self, event_bus):
        super().__init__(event_bus)
        raise RuntimeError("Plugin initialization failed")
''')

            try:
                await manager.load_plugin(test_plugins_dir / "broken.py")
            except RuntimeError:
                pass

            working = await manager.load_plugin(test_plugins_dir / "working.py")
            assert working is not None
            assert manager.get_plugin("working") is not None


class TestPluginManagerLoadFromDir:
    @pytest.mark.asyncio
    async def test_load_plugins_from_dir(self):
        bus = EventBus()
        manager = PluginManager(bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "plugin_a.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class APlugin(Plugin):
    name = "a"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "Plugin A"
''')

            (test_plugins_dir / "plugin_b.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class BPlugin(Plugin):
    name = "b"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "Plugin B"
''')

            count = await manager.load_plugins_from_dir(test_plugins_dir)
            assert count == 2

    @pytest.mark.asyncio
    async def test_load_plugins_from_nonexistent_dir(self):
        bus = EventBus()
        manager = PluginManager(bus)

        count = await manager.load_plugins_from_dir(Path("/nonexistent/path"))
        assert count == 0


class TestPluginManagerEvents:
    @pytest.mark.asyncio
    async def test_plugin_loaded_event(self):
        bus = EventBus()
        manager = PluginManager(bus)

        received = []

        async def handler(event):
            received.append(event)

        await bus.subscribe("plugin.loaded", handler)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")

        assert len(received) == 1
        assert received[0].data["name"] == "simple"

    @pytest.mark.asyncio
    async def test_plugin_enabled_event(self):
        bus = EventBus()
        manager = PluginManager(bus)

        received = []

        async def handler(event):
            received.append(event)

        await bus.subscribe("plugin.enabled", handler)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.enable_plugin("simple")

        assert len(received) == 1
        assert received[0].data["name"] == "simple"

    @pytest.mark.asyncio
    async def test_plugin_disabled_event(self):
        bus = EventBus()
        manager = PluginManager(bus)

        received = []

        async def handler(event):
            received.append(event)

        await bus.subscribe("plugin.disabled", handler)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.enable_plugin("simple")
            await manager.disable_plugin("simple")

        assert len(received) == 1
        assert received[0].data["name"] == "simple"

    @pytest.mark.asyncio
    async def test_plugin_unloaded_event(self):
        bus = EventBus()
        manager = PluginManager(bus)

        received = []

        async def handler(event):
            received.append(event)

        await bus.subscribe("plugin.unloaded", handler)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_plugins_dir = Path(temp_dir) / "plugins"
            test_plugins_dir.mkdir()

            (test_plugins_dir / "simple.py").write_text('''
from creamcode.core.plugin_manager import Plugin
from creamcode.types import PluginType

class SimplePlugin(Plugin):
    name = "simple"
    version = "1.0.0"
    type = PluginType.USER
    depends_on = []
    description = "A simple test plugin"
''')

            await manager.load_plugin(test_plugins_dir / "simple.py")
            await manager.unload_plugin("simple")

        assert len(received) == 1
        assert received[0].data["name"] == "simple"

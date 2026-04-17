from __future__ import annotations

import pytest

from creamcode.core.event_bus import EventBus
from creamcode.tools.registry import ToolRegistry
from creamcode.tools.decorator import set_global_registry
from creamcode.tools.builtins import register_builtins


class TestBuiltinToolsImport:
    def test_import_bash_tool(self):
        from creamcode.tools import bash
        assert bash is not None

    def test_import_file_tools(self):
        from creamcode.tools import file
        assert file is not None

    def test_import_web_tools(self):
        from creamcode.tools import web
        assert web is not None


class TestBuiltinToolsRegistration:
    @pytest.fixture
    def registry(self):
        bus = EventBus()
        reg = ToolRegistry(bus)
        set_global_registry(reg)
        register_builtins(reg)
        yield reg
        set_global_registry(None)

    def test_bash_registered(self, registry):
        assert registry.has_tool("Bash")
        tool_def = registry.get_tool("Bash")
        assert tool_def is not None
        assert tool_def.name == "Bash"
        assert "shell" in tool_def.description.lower() or "command" in tool_def.description.lower()

    def test_file_read_registered(self, registry):
        assert registry.has_tool("FileRead")
        tool_def = registry.get_tool("FileRead")
        assert tool_def is not None
        assert tool_def.name == "FileRead"

    def test_file_write_registered(self, registry):
        assert registry.has_tool("FileWrite")
        tool_def = registry.get_tool("FileWrite")
        assert tool_def is not None
        assert tool_def.name == "FileWrite"

    def test_file_edit_registered(self, registry):
        assert registry.has_tool("FileEdit")
        tool_def = registry.get_tool("FileEdit")
        assert tool_def is not None
        assert tool_def.name == "FileEdit"

    def test_web_fetch_registered(self, registry):
        assert registry.has_tool("WebFetch")
        tool_def = registry.get_tool("WebFetch")
        assert tool_def is not None
        assert tool_def.name == "WebFetch"

    def test_web_search_registered(self, registry):
        assert registry.has_tool("WebSearch")
        tool_def = registry.get_tool("WebSearch")
        assert tool_def is not None
        assert tool_def.name == "WebSearch"


class TestBuiltinToolsCount:
    @pytest.fixture
    def registry(self):
        bus = EventBus()
        reg = ToolRegistry(bus)
        set_global_registry(reg)
        register_builtins(reg)
        yield reg
        set_global_registry(None)

    def test_builtin_tools_count(self, registry):
        expected_tools = {"Bash", "FileRead", "FileWrite", "FileEdit", "WebFetch", "WebSearch"}
        registered_names = {t.name for t in registry.list_tools()}
        assert expected_tools.issubset(registered_names), f"Missing tools: {expected_tools - registered_names}"

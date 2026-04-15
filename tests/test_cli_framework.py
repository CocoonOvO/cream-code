from __future__ import annotations

import asyncio
import pytest
from io import StringIO
import sys

from creamcode.core.cli_framework import (
    CommandInfo,
    CLIRegistry,
    CLIApp,
    InteractiveMode,
)


class TestCLIRegistry:
    def test_register_command(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "config_plugin", "List config")

        info = registry.get_handler("config", "list")
        assert info is handler

    def test_register_multiple_commands_same_namespace(self):
        registry = CLIRegistry()

        async def handler1(args):
            return 0

        async def handler2(args):
            return 0

        registry.register("config", "list", handler1, "config_plugin")
        registry.register("config", "get", handler2, "config_plugin")

        assert registry.get_handler("config", "list") is handler1
        assert registry.get_handler("config", "get") is handler2

    def test_unregister_command(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "config_plugin")
        registry.unregister("config", "list")

        assert registry.get_handler("config", "list") is None

    def test_unregister_nonexistent_command(self):
        registry = CLIRegistry()
        registry.unregister("nonexistent", "command")
        assert registry.get_handler("nonexistent", "command") is None

    def test_list_commands_all(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "plugin1")
        registry.register("plugin", "add", handler, "plugin2")

        commands = registry.list_commands()
        assert len(commands) == 2

    def test_list_commands_by_namespace(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "plugin1")
        registry.register("config", "get", handler, "plugin1")
        registry.register("plugin", "add", handler, "plugin2")

        config_commands = registry.list_commands("config")
        assert len(config_commands) == 2
        assert all(cmd.namespace == "config" for cmd in config_commands)

        plugin_commands = registry.list_commands("plugin")
        assert len(plugin_commands) == 1

    def test_list_commands_nonexistent_namespace(self):
        registry = CLIRegistry()
        commands = registry.list_commands("nonexistent")
        assert len(commands) == 0

    def test_list_namespaces(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "plugin1")
        registry.register("plugin", "add", handler, "plugin2")

        namespaces = registry.list_namespaces()
        assert "config" in namespaces
        assert "plugin" in namespaces

    def test_namespace_isolation(self):
        registry = CLIRegistry()

        async def config_handler(args):
            return "config_handler"

        async def plugin_handler(args):
            return "plugin_handler"

        registry.register("config", "list", config_handler, "plugin1")
        registry.register("plugin", "list", plugin_handler, "plugin2")

        assert registry.get_handler("config", "list") is config_handler
        assert registry.get_handler("plugin", "list") is plugin_handler
        assert registry.get_handler("config", "list") is not registry.get_handler("plugin", "list")

    def test_command_info_stored(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "my_plugin", "List configuration")

        commands = registry.list_commands("config")
        assert len(commands) == 1
        cmd_info = commands[0]
        assert cmd_info.namespace == "config"
        assert cmd_info.name == "list"
        assert cmd_info.handler_path == "my_plugin.list"
        assert cmd_info.description == "List configuration"


class TestCLIApp:
    def test_parse_version_flag(self, capsys):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse(["--version"])
        assert result is None

        captured = capsys.readouterr()
        assert f"creamcode {cli.VERSION}" in captured.out

    def test_parse_debug_flag(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse(["--debug"])
        assert result == ("_builtin", "debug", {})

    def test_parse_plugin_command(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse(["config", "list"])
        assert result is not None
        namespace, command, kwargs = result
        assert namespace == "config"
        assert command == "list"

    def test_parse_command_with_args(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse(["config", "get", "--key", "test_key"])
        assert result is not None
        namespace, command, kwargs = result
        assert namespace == "config"
        assert command == "get"

    def test_parse_empty_args(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse([])
        assert result is None

    def test_parse_invalid_command_format(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse(["only_one"])
        assert result is None

    def test_execute_unknown_command(self, capsys):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = asyncio.run(cli.execute("unknown", "cmd", {}))
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown command" in captured.err

    def test_execute_valid_command(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)
        executed = False

        async def handler(args):
            nonlocal executed
            executed = True
            return 0

        registry.register("test", "cmd", handler, "test_plugin")

        result = asyncio.run(cli.execute("test", "cmd", {}))
        assert result == 0
        assert executed is True

    def test_execute_command_exception(self, capsys):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        async def handler(args):
            raise RuntimeError("Test error")

        registry.register("test", "cmd", handler, "test_plugin")

        result = asyncio.run(cli.execute("test", "cmd", {}))
        assert result == 1
        captured = capsys.readouterr()
        assert "Test error" in captured.err

    def test_run_returns_code(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        exit_code = cli.run(["--version"])
        assert exit_code == 0

    def test_print_help_no_namespace(self, capsys):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        cli.print_help()
        captured = capsys.readouterr()
        assert "Usage:" in captured.out
        assert "--version" in captured.out

    def test_print_help_with_namespace(self, capsys):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "plugin", "List config")

        cli = CLIApp(registry)
        cli.print_help("config")
        captured = capsys.readouterr()
        assert "config" in captured.out
        assert "list" in captured.out


class TestInteractiveMode:
    def test_print_welcome(self, capsys):
        registry = CLIRegistry()
        cli = CLIApp(registry)
        mode = InteractiveMode(cli)

        mode.print_welcome()
        captured = capsys.readouterr()
        assert "Welcome" in captured.out

    def test_print_prompt(self, capsys):
        registry = CLIRegistry()
        cli = CLIApp(registry)
        mode = InteractiveMode(cli)

        mode.print_prompt()
        captured = capsys.readouterr()
        assert ">" in captured.out


class TestEdgeCases:
    def test_registry_after_unregister_all_commands_in_namespace(self):
        registry = CLIRegistry()

        async def handler(args):
            return 0

        registry.register("config", "list", handler, "plugin")
        registry.register("config", "get", handler, "plugin")

        registry.unregister("config", "list")
        registry.unregister("config", "get")

        assert registry.list_commands("config") == []
        assert "config" not in registry.list_namespaces()

    def test_overwrite_existing_command(self):
        registry = CLIRegistry()

        async def handler1(args):
            return "handler1"

        async def handler2(args):
            return "handler2"

        registry.register("config", "list", handler1, "plugin")
        registry.register("config", "list", handler2, "plugin")

        assert registry.get_handler("config", "list") is handler2
        commands = registry.list_commands("config")
        assert len(commands) == 1

    def test_cli_app_command_args_parsing(self):
        registry = CLIRegistry()
        cli = CLIApp(registry)

        result = cli.parse(["config", "get", "--key", "mykey", "--value", "myvalue"])
        assert result is not None
        namespace, command, kwargs = result
        assert namespace == "config"
        assert command == "get"

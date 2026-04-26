from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import argparse
import sys

from .event_bus import event_bus


@dataclass
class CommandInfo:
    namespace: str
    name: str
    handler_path: str
    description: str | None = None


class CLIRegistry:
    def __init__(self):
        self._commands: dict[tuple[str, str], CommandInfo] = {}
        self._handlers: dict[tuple[str, str], Callable] = {}
        self._namespaces: dict[str, set[str]] = {}

    def register(
        self,
        namespace: str,
        name: str,
        handler: Callable,
        plugin: str,
        description: str | None = None
    ) -> None:
        key = (namespace, name)
        self._commands[key] = CommandInfo(
            namespace=namespace,
            name=name,
            handler_path=f"{plugin}.{name}",
            description=description
        )
        self._handlers[key] = handler
        if namespace not in self._namespaces:
            self._namespaces[namespace] = set()
        self._namespaces[namespace].add(name)

    def unregister(self, namespace: str, name: str) -> None:
        key = (namespace, name)
        if key in self._commands:
            del self._commands[key]
        if key in self._handlers:
            del self._handlers[key]
        if namespace in self._namespaces and name in self._namespaces[namespace]:
            self._namespaces[namespace].discard(name)
            if not self._namespaces[namespace]:
                del self._namespaces[namespace]

    def unregister_namespace(self, namespace: str) -> None:
        if namespace not in self._namespaces:
            return
        for name in list(self._namespaces[namespace]):
            self.unregister(namespace, name)

    def get_handler(self, namespace: str, name: str) -> Callable | None:
        return self._handlers.get((namespace, name))

    def list_commands(self, namespace: str | None = None) -> list[CommandInfo]:
        if namespace is not None:
            return [cmd for key, cmd in self._commands.items() if key[0] == namespace]
        return list(self._commands.values())

    def list_namespaces(self) -> list[str]:
        return list(self._namespaces.keys())


class CLIApp:
    VERSION = "0.1.0"

    _cli = event_bus.create_space("cli")

    def __init__(self, registry: CLIRegistry):
        self.registry = registry
        self._parser = argparse.ArgumentParser(
            prog="creamcode",
            description="Lightweight AI coding CLI",
            add_help=False
        )
        self._parser.add_argument("--version", action="store_true", help="Show version")
        self._parser.add_argument("--debug", action="store_true", help="Enable debug mode")
        self._parser.add_argument("command", nargs="*", help="Command to execute")

    @_cli.event("start")
    async def initialize(self):
        """CLI 初始化"""
        pass

    @_cli.event("command")
    async def execute(self, namespace: str, command: str, args: dict) -> int:
        handler = self.registry.get_handler(namespace, command)
        if handler is None:
            print(f"Error: Unknown command '{namespace} {command}'", file=sys.stderr)
            return 1
        try:
            result = handler(args)
            if hasattr(result, "__await__"):
                await result
            return 0
        except Exception as e:
            print(f"Error executing command: {e}", file=sys.stderr)
            return 1

    def parse(self, args: list[str] | None = None) -> tuple[str, str, dict] | None:
        if args is None:
            args = sys.argv[1:]

        parsed, unknown = self._parser.parse_known_args(args)

        if parsed.version:
            print(f"creamcode {self.VERSION}")
            return None

        if parsed.debug:
            return ("_builtin", "debug", {})

        command = parsed.command
        if not command:
            return None

        if len(command) < 2:
            return None

        namespace, name = command[0], command[1]
        cmd_args = command[2:] if len(command) > 2 else []

        kwargs = {"_args": cmd_args}

        return (namespace, name, kwargs)

    def run(self, args: list[str] | None = None) -> int:
        parsed = self.parse(args)
        if parsed is None:
            self.print_help()
            return 0

        namespace, command, kwargs = parsed
        if namespace == "_builtin":
            return 0

        return 1

    def print_help(self, namespace: str | None = None):
        if namespace:
            commands = self.registry.list_commands(namespace)
            if commands:
                print(f"\nCommands in '{namespace}' namespace:")
                for cmd in commands:
                    desc = cmd.description or ""
                    print(f"  {cmd.name} - {desc}")
            else:
                print(f"\nNo commands in namespace '{namespace}'")
        else:
            print("\nUsage: creamcode <namespace> <command> [args]")
            print("\nNamespaces:")
            for ns in self.registry.list_namespaces():
                print(f"  {ns}")
            print("\nBuiltin options:")
            print("  --version   Show version")
            print("  --debug     Enable debug mode")


class InteractiveMode:
    _cli = event_bus.create_space("cli")

    def __init__(self, cli: CLIApp):
        self.cli = cli

    @_cli.event("interactive")
    async def run(self):
        """交互模式启动"""
        self.print_welcome()
        while True:
            self.print_prompt()
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting interactive mode.")
                break

            line = line.strip()
            if not line:
                continue

            if line == "exit":
                break
            elif line == "help":
                self.cli.print_help()
            else:
                result = self.cli.run([line])
                if result != 0:
                    print(f"Command failed with exit code {result}")

    def print_welcome(self):
        print("Welcome to creamcode interactive mode. Type 'help' for commands, 'exit' to quit.")

    def print_prompt(self):
        print("> ", end="")

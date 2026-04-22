from __future__ import annotations

import logging
from typing import Any

from creamcode.tools.registry import ToolRegistry

from .protocol import MCPServerConfig
from .client import MCPClient
from .tool_adapter import MCPToolAdapter


class MCPServerManager:
    def __init__(self) -> None:
        self._servers: dict[str, MCPClient] = {}
        self._configs: dict[str, MCPServerConfig] = {}
        self._tool_adapters: dict[str, MCPToolAdapter] = {}
        self._logger = logging.getLogger("creamcode.mcp.manager")

    def add_server(self, config: MCPServerConfig) -> None:
        if config.name in self._configs:
            raise ValueError(f"Server '{config.name}' already exists")

        self._configs[config.name] = config
        client = MCPClient(config)
        self._servers[config.name] = client
        self._tool_adapters[config.name] = MCPToolAdapter(client)
        self._logger.info(f"Added MCP server config: {config.name}")

    def remove_server(self, name: str) -> None:
        if name not in self._configs and name not in self._servers:
            raise KeyError(f"Server '{name}' not found")

        if name in self._servers:
            client = self._servers[name]
            if client.is_connected:
                raise ValueError(f"Cannot remove running server '{name}'. Stop it first.")

        if name in self._configs:
            del self._configs[name]
        if name in self._servers:
            del self._servers[name]
        if name in self._tool_adapters:
            del self._tool_adapters[name]
        self._logger.info(f"Removed MCP server config: {name}")

    async def start_server(self, name: str) -> None:
        if name not in self._servers:
            raise KeyError(f"Server '{name}' not found")

        client = self._servers[name]
        await client.connect()
        await client.initialize()
        self._logger.info(f"Started MCP server: {name}")

    async def stop_server(self, name: str) -> None:
        if name not in self._servers:
            raise KeyError(f"Server '{name}' not found")

        client = self._servers[name]
        await client.disconnect()
        self._logger.info(f"Stopped MCP server: {name}")

    async def start_all(self) -> None:
        for name in list(self._servers.keys()):
            try:
                await self.start_server(name)
            except Exception as e:
                self._logger.error(f"Failed to start server '{name}': {e}")

    async def stop_all(self) -> None:
        for name in list(self._servers.keys()):
            try:
                await self.stop_server(name)
            except Exception as e:
                self._logger.error(f"Failed to stop server '{name}': {e}")

    def get_server(self, name: str) -> MCPClient | None:
        return self._servers.get(name)

    def list_servers(self) -> list[str]:
        return list(self._servers.keys())

    def get_adapter(self, name: str) -> MCPToolAdapter | None:
        return self._tool_adapters.get(name)

    async def register_tools_to_registry(self, registry: ToolRegistry) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}

        for name, adapter in self._tool_adapters.items():
            try:
                adapter.set_registry(registry)
                registered = await adapter.discover_and_register()
                results[name] = registered
                self._logger.info(f"Registered {len(registered)} tools from '{name}'")
            except Exception as e:
                self._logger.error(f"Failed to register tools from '{name}': {e}")
                results[name] = []

        return results

    def get_all_tools(self) -> list[dict[str, Any]]:
        all_tools: list[dict[str, Any]] = []
        for name, adapter in self._tool_adapters.items():
            client = self._servers[name]
            if client.is_connected:
                try:
                    import inspect
                    if inspect.iscoroutinefunction(client.list_tools):
                        raise RuntimeError("get_all_tools should not be called when servers have async list_tools - use get_all_tools_async instead")
                    tools = client.list_tools()
                    all_tools.extend(tools)
                except Exception as e:
                    self._logger.warning(f"Failed to get tools from '{name}': {e}")
        return all_tools

    async def get_all_tools_async(self) -> list[dict[str, Any]]:
        all_tools: list[dict[str, Any]] = []
        for name, adapter in self._tool_adapters.items():
            client = self._servers[name]
            if client.is_connected:
                try:
                    tools = await client.list_tools()
                    all_tools.extend(tools)
                except Exception as e:
                    self._logger.warning(f"Failed to get tools from '{name}': {e}")
        return all_tools
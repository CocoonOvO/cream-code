from __future__ import annotations

import logging
from typing import Any

from creamcode.types import Tool
from creamcode.tools.registry import ToolRegistry

from .client import MCPClient


class MCPToolAdapter:
    def __init__(self, mcp_client: MCPClient) -> None:
        self.mcp_client = mcp_client
        self._tool_registry: ToolRegistry | None = None
        self._logger = logging.getLogger(f"creamcode.mcp.adapter.{mcp_client.config.name}")

    def set_registry(self, registry: ToolRegistry) -> None:
        self._tool_registry = registry

    async def discover_and_register(self) -> list[str]:
        if self._tool_registry is None:
            raise ValueError("Tool registry not set")

        tools = await self.mcp_client.list_tools()
        registered_names: list[str] = []

        for mcp_tool in tools:
            try:
                tool = self._convert_mcp_tool(mcp_tool)
                handler = self._create_handler(mcp_tool["name"])
                self._tool_registry.register(tool, handler)
                registered_names.append(tool.name)
                self._logger.info(f"Registered MCP tool: {tool.name}")
            except Exception as e:
                self._logger.error(f"Failed to register tool {mcp_tool.get('name', 'unknown')}: {e}")

        return registered_names

    def _convert_mcp_tool(self, mcp_tool: dict[str, Any]) -> Tool:
        name = mcp_tool.get("name", "")
        description = mcp_tool.get("description", "")
        input_schema = mcp_tool.get("inputSchema", {})

        parameters = self._convert_input_schema(input_schema)

        anthropic_schema = self._build_anthropic_schema(name, description, input_schema)
        openai_function = self._build_openai_function(name, description, input_schema)

        return Tool(
            name=name,
            description=description,
            parameters=parameters,
            anthropic_schema=anthropic_schema,
            openai_function=openai_function,
            metadata={"source": "mcp", "server": self.mcp_client.config.name}
        )

    def _convert_input_schema(self, input_schema: dict[str, Any]) -> dict[str, Any]:
        if not input_schema:
            return {"type": "object", "properties": {}}

        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        converted_props: dict[str, Any] = {}
        for prop_name, prop_value in properties.items():
            converted_prop: dict[str, Any] = {
                "type": prop_value.get("type", "string"),
                "description": prop_value.get("description", "")
            }
            if prop_name in required:
                converted_prop["required"] = True
            if "default" in prop_value:
                converted_prop["default"] = prop_value["default"]
            converted_props[prop_name] = converted_prop

        return {
            "type": "object",
            "properties": converted_props,
            "required": required
        }

    def _build_anthropic_schema(self, name: str, description: str, input_schema: dict[str, Any]) -> dict[str, Any]:
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        anthropic_props: dict[str, Any] = {}
        for prop_name, prop_value in properties.items():
            prop_type = prop_value.get("type", "string")
            if prop_type == "array":
                item_type = prop_value.get("items", {}).get("type", "string")
                anthropic_type = f"list<{item_type}>"
            elif prop_type == "object":
                anthropic_type = "object"
            else:
                anthropic_type = prop_type

            anthropic_props[prop_name] = {
                "type": anthropic_type,
                "description": prop_value.get("description", "")
            }

        return {
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": anthropic_props,
                "required": required
            }
        }

    def _build_openai_function(self, name: str, description: str, input_schema: dict[str, Any]) -> dict[str, Any]:
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        openai_props: dict[str, Any] = {}
        for prop_name, prop_value in properties.items():
            openai_props[prop_name] = {
                "type": prop_value.get("type", "string"),
                "description": prop_value.get("description", "")
            }

        return {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": openai_props,
                "required": required
            }
        }

    def _create_handler(self, tool_name: str):
        async def handler(**kwargs: Any) -> str:
            try:
                result = await self.mcp_client.call_tool(tool_name, kwargs)
                if isinstance(result, dict):
                    content = result.get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        return content[0].get("text", str(result))
                    return str(result)
                return str(result)
            except Exception as e:
                self._logger.error(f"MCP tool {tool_name} failed: {e}")
                raise

        return handler

    async def execute_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return await self.mcp_client.call_tool(tool_name, arguments)
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock

from creamcode.mcp.tool_adapter import MCPToolAdapter
from creamcode.mcp.client import MCPClient
from creamcode.mcp.protocol import MCPServerConfig


@pytest.fixture
def mock_mcp_client():
    config = MCPServerConfig(name="test-server", command="node", args=["server.js"])
    client = Mock(spec=MCPClient)
    client.config = config
    client.list_tools = AsyncMock(return_value=[])
    client.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "result"}]})
    return client


@pytest.fixture
def mock_registry():
    registry = Mock()
    registry.register = Mock()
    return registry


class TestMCPToolAdapter:
    @pytest.mark.asyncio
    async def test_discover_and_register_no_tools(self, mock_mcp_client, mock_registry):
        mock_mcp_client.list_tools.return_value = []

        adapter = MCPToolAdapter(mock_mcp_client)
        adapter.set_registry(mock_registry)

        registered = await adapter.discover_and_register()

        assert registered == []
        mock_registry.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_and_register_with_tools(self, mock_mcp_client, mock_registry):
        mock_mcp_client.list_tools.return_value = [
            {
                "name": "browser_navigate",
                "description": "Navigate to a URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_screenshot",
                "description": "Take a screenshot",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fullPage": {"type": "boolean", "description": "Capture full page"}
                    }
                }
            }
        ]

        adapter = MCPToolAdapter(mock_mcp_client)
        adapter.set_registry(mock_registry)

        registered = await adapter.discover_and_register()

        assert len(registered) == 2
        assert "browser_navigate" in registered
        assert "browser_screenshot" in registered
        assert mock_registry.register.call_count == 2

    def test_convert_mcp_tool_basic(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        mcp_tool = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string", "description": "First argument"}
                }
            }
        }

        tool = adapter._convert_mcp_tool(mcp_tool)

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.parameters["type"] == "object"
        assert "arg1" in tool.parameters["properties"]
        assert tool.metadata["source"] == "mcp"
        assert tool.metadata["server"] == "test-server"

    def test_convert_mcp_tool_with_required_fields(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        mcp_tool = {
            "name": "tool_with_required",
            "description": "Tool with required fields",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "required_arg": {"type": "string", "description": "Required"},
                    "optional_arg": {"type": "number", "description": "Optional"}
                },
                "required": ["required_arg"]
            }
        }

        tool = adapter._convert_mcp_tool(mcp_tool)

        assert "required_arg" in tool.parameters["required"]
        assert "optional_arg" not in tool.parameters["required"]

    def test_convert_input_schema_empty(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        result = adapter._convert_input_schema({})

        assert result == {"type": "object", "properties": {}}

    def test_convert_input_schema_with_properties(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        input_schema = {
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "number", "description": "User age"}
            },
            "required": ["name"]
        }

        result = adapter._convert_input_schema(input_schema)

        assert result["type"] == "object"
        assert "name" in result["properties"]
        assert result["properties"]["name"]["type"] == "string"
        assert result["properties"]["name"]["description"] == "User name"
        assert result["properties"]["age"]["type"] == "number"

    def test_convert_input_schema_with_defaults(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        input_schema = {
            "properties": {
                "timeout": {"type": "number", "description": "Timeout", "default": 30}
            }
        }

        result = adapter._convert_input_schema(input_schema)

        assert result["properties"]["timeout"]["default"] == 30

    def test_build_anthropic_schema(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        input_schema = {
            "properties": {
                "url": {"type": "string", "description": "URL to visit"}
            },
            "required": ["url"]
        }

        result = adapter._build_anthropic_schema("navigate", "Navigate to URL", input_schema)

        assert result["name"] == "navigate"
        assert result["description"] == "Navigate to URL"
        assert "url" in result["input_schema"]["properties"]
        assert result["input_schema"]["required"] == ["url"]

    def test_build_anthropic_schema_with_array_type(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        input_schema = {
            "properties": {
                "items": {"type": "array", "items": {"type": "string"}, "description": "List of items"}
            }
        }

        result = adapter._build_anthropic_schema("process_items", "Process items", input_schema)

        assert result["input_schema"]["properties"]["items"]["type"] == "list<string>"

    def test_build_openai_function(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        input_schema = {
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }

        result = adapter._build_openai_function("search", "Search for something", input_schema)

        assert result["name"] == "search"
        assert result["description"] == "Search for something"
        assert "query" in result["parameters"]["properties"]
        assert result["parameters"]["required"] == ["query"]

    @pytest.mark.asyncio
    async def test_execute_mcp_tool(self, mock_mcp_client):
        mock_mcp_client.call_tool.return_value = {"content": [{"type": "text", "text": "executed"}]}

        adapter = MCPToolAdapter(mock_mcp_client)

        result = await adapter.execute_mcp_tool("my_tool", {"arg": "value"})

        mock_mcp_client.call_tool.assert_called_once_with("my_tool", {"arg": "value"})
        assert result["content"][0]["text"] == "executed"

    def test_set_registry(self, mock_mcp_client, mock_registry):
        adapter = MCPToolAdapter(mock_mcp_client)
        adapter.set_registry(mock_registry)

        assert adapter._tool_registry == mock_registry

    def test_set_registry_twice(self, mock_mcp_client, mock_registry):
        adapter = MCPToolAdapter(mock_mcp_client)
        adapter.set_registry(mock_registry)

        new_registry = Mock()
        adapter.set_registry(new_registry)

        assert adapter._tool_registry == new_registry


class TestMCPToolAdapterErrors:
    @pytest.mark.asyncio
    async def test_discover_and_register_without_registry(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        with pytest.raises(ValueError, match="Tool registry not set"):
            await adapter.discover_and_register()

    def test_convert_mcp_tool_missing_fields(self, mock_mcp_client):
        adapter = MCPToolAdapter(mock_mcp_client)

        mcp_tool = {"name": "incomplete"}

        tool = adapter._convert_mcp_tool(mcp_tool)

        assert tool.name == "incomplete"
        assert tool.description == ""
        assert tool.parameters == {"type": "object", "properties": {}}
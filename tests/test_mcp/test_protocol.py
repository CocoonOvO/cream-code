from __future__ import annotations

import pytest

from creamcode.mcp.protocol import (
    MCPRequest, MCPResponse, MCPServerConfig, MCPTool, MCPResource, MCPPrompt
)


class TestMCPRequest:
    def test_create_empty_request(self):
        request = MCPRequest()
        assert request.jsonrpc == "2.0"
        assert request.id is None
        assert request.method == ""
        assert request.params is None

    def test_create_request_with_values(self):
        request = MCPRequest(id=1, method="tools/list", params={"key": "value"})
        assert request.jsonrpc == "2.0"
        assert request.id == 1
        assert request.method == "tools/list"
        assert request.params == {"key": "value"}

    def test_to_dict(self):
        request = MCPRequest(id=1, method="initialize", params={"protocolVersion": "2024-11-05"})
        result = request.to_dict()
        assert result == {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }

    def test_to_dict_without_optional_fields(self):
        request = MCPRequest(method="ping")
        result = request.to_dict()
        assert result == {
            "jsonrpc": "2.0",
            "method": "ping"
        }
        assert "id" not in result
        assert "params" not in result

    def test_from_dict(self):
        data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        request = MCPRequest.from_dict(data)
        assert request.jsonrpc == "2.0"
        assert request.id == 2
        assert request.method == "tools/list"
        assert request.params == {}

    def test_from_dict_with_defaults(self):
        data = {"method": "ping"}
        request = MCPRequest.from_dict(data)
        assert request.jsonrpc == "2.0"
        assert request.id is None
        assert request.method == "ping"
        assert request.params is None


class TestMCPResponse:
    def test_create_empty_response(self):
        response = MCPResponse()
        assert response.jsonrpc == "2.0"
        assert response.id is None
        assert response.result is None
        assert response.error is None

    def test_create_response_with_result(self):
        response = MCPResponse(id=1, result={"tools": []})
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result == {"tools": []}
        assert response.error is None

    def test_create_response_with_error(self):
        response = MCPResponse(id=1, error={"code": -32600, "message": "Invalid Request"})
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result is None
        assert response.error == {"code": -32600, "message": "Invalid Request"}

    def test_to_dict_with_result(self):
        response = MCPResponse(id=1, result={"success": True})
        result = response.to_dict()
        assert result == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"success": True}
        }

    def test_to_dict_with_error(self):
        response = MCPResponse(id=1, error={"code": -32600, "message": "Invalid"})
        result = response.to_dict()
        assert result == {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid"}
        }

    def test_from_dict(self):
        data = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"tools": [{"name": "test"}]}
        }
        response = MCPResponse.from_dict(data)
        assert response.jsonrpc == "2.0"
        assert response.id == 2
        assert response.result == {"tools": [{"name": "test"}]}
        assert response.error is None

    def test_is_error_property(self):
        response_with_error = MCPResponse(error={"code": -32600})
        assert response_with_error.is_error is True

        response_with_result = MCPResponse(result={"success": True})
        assert response_with_result.is_error is False


class TestMCPServerConfig:
    def test_create_config(self):
        config = MCPServerConfig(name="test-server", command="npx", args=["-y", "server"])
        assert config.name == "test-server"
        assert config.command == "npx"
        assert config.args == ["-y", "server"]
        assert config.env == {}
        assert config.cwd is None

    def test_create_config_with_all_fields(self):
        config = MCPServerConfig(
            name="chrome-devtools",
            command="npx",
            args=["-y", "@anthropic/mcp-server-chrome-devtools"],
            env={"DEBUG": "1"},
            cwd="/path/to/project"
        )
        assert config.name == "chrome-devtools"
        assert config.command == "npx"
        assert config.args == ["-y", "@anthropic/mcp-server-chrome-devtools"]
        assert config.env == {"DEBUG": "1"}
        assert config.cwd == "/path/to/project"

    def test_config_empty_name_raises(self):
        with pytest.raises(ValueError, match="Server name cannot be empty"):
            MCPServerConfig(name="", command="npx")

    def test_config_empty_command_raises(self):
        with pytest.raises(ValueError, match="Command cannot be empty"):
            MCPServerConfig(name="test", command="")


class TestMCPTool:
    def test_create_tool(self):
        tool = MCPTool(
            name="browser_navigate",
            description="Navigate to a URL",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}}
        )
        assert tool.name == "browser_navigate"
        assert tool.description == "Navigate to a URL"
        assert tool.input_schema == {"type": "object", "properties": {"url": {"type": "string"}}}


class TestMCPResource:
    def test_create_resource(self):
        resource = MCPResource(
            uri="file:///path/to/file.txt",
            name="myfile.txt",
            description="A text file",
            mime_type="text/plain"
        )
        assert resource.uri == "file:///path/to/file.txt"
        assert resource.name == "myfile.txt"
        assert resource.description == "A text file"
        assert resource.mime_type == "text/plain"


class TestMCPPrompt:
    def test_create_prompt(self):
        prompt = MCPPrompt(
            name="summarize",
            description="Summarize content",
            arguments=[{"name": "text", "type": "string", "description": "Text to summarize"}]
        )
        assert prompt.name == "summarize"
        assert prompt.description == "Summarize content"
        assert prompt.arguments == [{"name": "text", "type": "string", "description": "Text to summarize"}]
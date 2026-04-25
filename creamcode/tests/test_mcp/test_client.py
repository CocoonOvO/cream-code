from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock

from creamcode.mcp.client import (
    MCPClient, MCPClientError, MCPConnectionError, MCPProtocolError
)
from creamcode.mcp.protocol import MCPServerConfig


@pytest.fixture
def server_config():
    return MCPServerConfig(
        name="test-server",
        command="node",
        args=["server.js"]
    )


@pytest.fixture
def mock_process():
    mock_stdout = Mock()
    mock_stdout.readline = Mock(return_value='{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {}, "serverInfo": {"name": "test", "version": "1.0"}}}')

    mock_stdin = Mock()
    mock_stdin.write = Mock()
    mock_stdin.flush = Mock()

    process_mock = Mock()
    process_mock.stdout = mock_stdout
    process_mock.stdin = mock_stdin
    process_mock.poll = Mock(return_value=None)
    process_mock.terminate = Mock()
    process_mock.wait = Mock()

    return process_mock


class TestMCPClient:
    @pytest.mark.asyncio
    async def test_connect_starts_process(self, server_config, mock_process):
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()

            assert client.is_connected

    @pytest.mark.asyncio
    async def test_disconnect_stops_process(self, server_config, mock_process):
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.disconnect()

            assert not client.is_connected
            mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_sends_request(self, server_config, mock_process):
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()

            result = await client.initialize()

            assert result["protocolVersion"] == "2024-11-05"
            assert result["serverInfo"]["name"] == "test"
            assert client.server_info == {"name": "test", "version": "1.0"}

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, server_config, mock_process):
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()

            result1 = await client.initialize()
            result2 = await client.initialize()

            assert result1["serverInfo"] == result2
            assert result1["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_list_tools(self, server_config, mock_process):
        response_data = '{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "tool1", "description": "A tool", "inputSchema": {}}]}}'
        mock_process.stdout.readline = Mock(return_value=response_data)

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.initialize()

            tools = await client.list_tools()

            assert len(tools) == 1
            assert tools[0]["name"] == "tool1"

    @pytest.mark.asyncio
    async def test_list_resources(self, server_config, mock_process):
        response_data = '{"jsonrpc": "2.0", "id": 3, "result": {"resources": []}}'
        mock_process.stdout.readline = Mock(return_value=response_data)

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.initialize()

            resources = await client.list_resources()

            assert resources == []

    @pytest.mark.asyncio
    async def test_list_prompts(self, server_config, mock_process):
        response_data = '{"jsonrpc": "2.0", "id": 4, "result": {"prompts": []}}'
        mock_process.stdout.readline = Mock(return_value=response_data)

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.initialize()

            prompts = await client.list_prompts()

            assert prompts == []

    @pytest.mark.asyncio
    async def test_call_tool(self, server_config, mock_process):
        response_data = '{"jsonrpc": "2.0", "id": 5, "result": {"content": [{"type": "text", "text": "success"}]}}'
        mock_process.stdout.readline = Mock(return_value=response_data)

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.initialize()

            result = await client.call_tool("my_tool", {"arg": "value"})

            assert result["content"][0]["text"] == "success"

    @pytest.mark.asyncio
    async def test_send_request_not_connected_raises(self, server_config):
        client = MCPClient(server_config)

        with pytest.raises(MCPConnectionError, match="Server not connected"):
            await client._send_request("test", {})

    @pytest.mark.asyncio
    async def test_read_response_timeout(self, server_config, mock_process):
        mock_process.stdout.readline = Mock(side_effect=asyncio.TimeoutError())

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()

            with pytest.raises(MCPProtocolError, match="Timeout reading response"):
                await client._read_response()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, server_config, mock_process):
        mock_process.stdout.readline = Mock(return_value="not valid json")

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()

            with pytest.raises(MCPProtocolError, match="Invalid JSON response"):
                await client._read_response()

    @pytest.mark.asyncio
    async def test_server_error_response(self, server_config, mock_process):
        error_response = '{"jsonrpc": "2.0", "id": 2, "error": {"code": -32600, "message": "Invalid Request"}}'

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.initialize()

            mock_process.stdout.readline.side_effect = [
                error_response,
                MCPConnectionError("Server closed connection")
            ]

            with pytest.raises(MCPProtocolError, match="Server error"):
                await client.list_tools()

    @pytest.mark.asyncio
    async def test_capabilities_property(self, server_config, mock_process):
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient(server_config)
            await client.connect()
            await client.initialize()

            assert client.capabilities == {}


class TestMCPClientErrors:
    def test_mcp_client_error_inheritance(self):
        assert issubclass(MCPConnectionError, MCPClientError)
        assert issubclass(MCPProtocolError, MCPClientError)

    def test_error_messages(self):
        error = MCPConnectionError("connection failed")
        assert str(error) == "connection failed"

        error = MCPProtocolError("protocol error")
        assert str(error) == "protocol error"
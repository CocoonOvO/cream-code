from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch

from creamcode.mcp.manager import MCPServerManager
from creamcode.mcp.protocol import MCPServerConfig


@pytest.fixture
def manager():
    return MCPServerManager()


@pytest.fixture
def server_config():
    return MCPServerConfig(name="test-server", command="node", args=["server.js"])


class TestMCPServerManager:
    def test_add_server(self, manager, server_config):
        manager.add_server(server_config)

        assert "test-server" in manager.list_servers()
        server = manager.get_server("test-server")
        assert server is not None
        assert server.config.name == "test-server"

    def test_add_duplicate_server_raises(self, manager, server_config):
        manager.add_server(server_config)

        with pytest.raises(ValueError, match="already exists"):
            manager.add_server(server_config)

    def test_remove_server(self, manager, server_config):
        manager.add_server(server_config)
        manager.remove_server("test-server")

        assert "test-server" not in manager.list_servers()
        assert manager.get_server("test-server") is None

    def test_remove_nonexistent_server_raises(self, manager):
        with pytest.raises(KeyError, match="not found"):
            manager.remove_server("nonexistent")

    @pytest.mark.asyncio
    async def test_start_server(self, manager, server_config):
        mock_client = Mock()
        mock_client.connect = AsyncMock()
        mock_client.initialize = AsyncMock()

        with patch.object(manager, "_servers", {"test-server": mock_client}):
            await manager.start_server("test-server")

            mock_client.connect.assert_called_once()
            mock_client.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_nonexistent_server_raises(self, manager):
        with pytest.raises(KeyError, match="not found"):
            await manager.start_server("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_server(self, manager, server_config):
        mock_client = Mock()
        mock_client.disconnect = AsyncMock()

        with patch.object(manager, "_servers", {"test-server": mock_client}):
            await manager.stop_server("test-server")

            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_nonexistent_server_raises(self, manager):
        with pytest.raises(KeyError, match="not found"):
            await manager.stop_server("nonexistent")

    @pytest.mark.asyncio
    async def test_start_all(self, manager):
        mock_client1 = Mock()
        mock_client1.connect = AsyncMock()
        mock_client1.initialize = AsyncMock()

        mock_client2 = Mock()
        mock_client2.connect = AsyncMock()
        mock_client2.initialize = AsyncMock()

        manager._servers = {
            "server1": mock_client1,
            "server2": mock_client2
        }
        manager._configs = {
            "server1": MCPServerConfig(name="server1", command="node"),
            "server2": MCPServerConfig(name="server2", command="node")
        }

        await manager.start_all()

        mock_client1.connect.assert_called_once()
        mock_client2.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_all_continues_on_error(self, manager):
        mock_client1 = Mock()
        mock_client1.connect = AsyncMock(side_effect=Exception("Failed"))
        mock_client1.initialize = AsyncMock()

        mock_client2 = Mock()
        mock_client2.connect = AsyncMock()
        mock_client2.initialize = AsyncMock()

        manager._servers = {
            "server1": mock_client1,
            "server2": mock_client2
        }
        manager._configs = {
            "server1": MCPServerConfig(name="server1", command="node"),
            "server2": MCPServerConfig(name="server2", command="node")
        }

        await manager.start_all()

        mock_client1.connect.assert_called_once()
        mock_client2.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all(self, manager):
        mock_client1 = Mock()
        mock_client1.disconnect = AsyncMock()

        mock_client2 = Mock()
        mock_client2.disconnect = AsyncMock()

        manager._servers = {
            "server1": mock_client1,
            "server2": mock_client2
        }

        await manager.stop_all()

        mock_client1.disconnect.assert_called_once()
        mock_client2.disconnect.assert_called_once()

    def test_get_adapter(self, manager, server_config):
        manager.add_server(server_config)

        adapter = manager.get_adapter("test-server")

        assert adapter is not None

    def test_get_nonexistent_adapter(self, manager):
        adapter = manager.get_adapter("nonexistent")

        assert adapter is None

    @pytest.mark.asyncio
    async def test_register_tools_to_registry(self, manager):
        mock_registry = Mock()

        mock_adapter1 = Mock()
        mock_adapter1.set_registry = Mock()
        mock_adapter1.discover_and_register = AsyncMock(return_value=["tool1", "tool2"])

        mock_adapter2 = Mock()
        mock_adapter2.set_registry = Mock()
        mock_adapter2.discover_and_register = AsyncMock(return_value=["tool3"])

        manager._tool_adapters = {
            "server1": mock_adapter1,
            "server2": mock_adapter2
        }

        results = await manager.register_tools_to_registry(mock_registry)

        assert results["server1"] == ["tool1", "tool2"]
        assert results["server2"] == ["tool3"]

    @pytest.mark.asyncio
    async def test_get_all_tools(self, manager):
        mock_client = Mock()
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[{"name": "test_tool"}])

        manager._servers = {"test-server": mock_client}
        manager._tool_adapters = {"test-server": Mock()}

        tools = await manager.get_all_tools_async()

        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    def test_get_all_tools_disconnected_server(self, manager):
        mock_client = Mock()
        mock_client.is_connected = False

        manager._servers = {"test-server": mock_client}
        manager._tool_adapters = {"test-server": Mock()}

        tools = manager.get_all_tools()

        assert len(tools) == 0


class TestMCPServerManagerIntegration:
    def test_full_lifecycle(self, manager, server_config):
        manager.add_server(server_config)

        assert "test-server" in manager.list_servers()

        server = manager.get_server("test-server")
        assert server is not None

        adapter = manager.get_adapter("test-server")
        assert adapter is not None

        manager.remove_server("test-server")

        assert "test-server" not in manager.list_servers()
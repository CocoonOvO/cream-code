from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any

from .protocol import MCPRequest, MCPResponse, MCPServerConfig


class MCPClientError(Exception):
    pass


class MCPConnectionError(MCPClientError):
    pass


class MCPProtocolError(MCPClientError):
    pass


class MCPClient:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._process: subprocess.Popen[str, str] | None = None
        self._request_id: int = 0
        self._initialized: bool = False
        self._server_info: dict[str, Any] | None = None
        self._capabilities: dict[str, Any] | None = None
        self._logger = logging.getLogger(f"creamcode.mcp.client.{config.name}")

    async def connect(self) -> None:
        if self._process is not None:
            return

        env = dict(self.config.env)
        env["NODE_PATH"] = env.get("NODE_PATH", "")

        try:
            self._process = subprocess.Popen(
                [self.config.command] + self.config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=self.config.cwd,
                text=True,
                bufsize=1
            )
            self._logger.info(f"Started MCP server: {self.config.name}")
        except Exception as e:
            raise MCPConnectionError(f"Failed to start server: {e}")

        await asyncio.sleep(0.1)

    async def disconnect(self) -> None:
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            self._initialized = False
            self._logger.info(f"Stopped MCP server: {self.config.name}")

    async def initialize(self) -> dict[str, Any]:
        if self._initialized:
            return self._server_info or {}

        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "creamcode",
                "version": "0.1.0"
            }
        }

        result = await self._send_request("initialize", params)
        self._server_info = result.get("serverInfo", {})
        self._capabilities = result.get("capabilities", {})
        self._initialized = True

        await self._send_notification("initialized", {"capabilities": result.get("capabilities", {})})

        self._logger.info(f"Initialized MCP server: {self.config.name}")
        return result

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    async def list_resources(self) -> list[dict[str, Any]]:
        result = await self._send_request("resources/list")
        return result.get("resources", [])

    async def list_prompts(self) -> list[dict[str, Any]]:
        result = await self._send_request("prompts/list")
        return result.get("prompts", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        params = {"name": name, "arguments": arguments}
        result = await self._send_request("tools/call", params)
        return result

    async def _send_request(self, method: str, params: dict | None = None) -> Any:
        if self._process is None or self._process.stdout is None or self._process.stdin is None:
            raise MCPConnectionError("Server not connected")

        self._request_id += 1
        request = MCPRequest(id=self._request_id, method=method, params=params)

        try:
            self._process.stdin.write(json.dumps(request.to_dict()) + "\n")
            self._process.stdin.flush()
        except BrokenPipeError as e:
            raise MCPConnectionError(f"Failed to send request: {e}")

        try:
            response = await self._read_response()
        except asyncio.TimeoutError:
            raise MCPProtocolError(f"Timeout waiting for response to {method}")

        if response.is_error:
            raise MCPProtocolError(f"Server error: {response.error}")

        return response.result

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        if self._process is None or self._process.stdin is None:
            return

        notification = MCPRequest(method=method, params=params)
        try:
            self._process.stdin.write(json.dumps(notification.to_dict()) + "\n")
            self._process.stdin.flush()
        except BrokenPipeError:
            pass

    async def _read_response(self) -> MCPResponse:
        if self._process is None or self._process.stdout is None:
            raise MCPConnectionError("Server not connected")

        loop = asyncio.get_event_loop()

        def read_line() -> str:
            line = self._process.stdout.readline()
            if not line:
                raise MCPConnectionError("Server closed connection")
            return line

        try:
            line = await asyncio.wait_for(
                loop.run_in_executor(None, read_line),
                timeout=30
            )
        except asyncio.TimeoutError:
            raise MCPProtocolError("Timeout reading response")

        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise MCPProtocolError(f"Invalid JSON response: {e}")

        return MCPResponse.from_dict(data)

    @property
    def is_connected(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def server_info(self) -> dict[str, Any] | None:
        return self._server_info

    @property
    def capabilities(self) -> dict[str, Any] | None:
        return self._capabilities
from typing import Callable, Any
import logging

from creamcode.core.event_bus import EventBus
from creamcode.types import Tool, ToolResult, Event


class ToolNotFoundError(Exception):
    pass


class ToolRegistry:
    def __init__(self, event_bus: EventBus):
        self._tools: dict[str, Tool] = {}
        self._handlers: dict[str, Callable] = {}
        self._event_bus = event_bus
        self._logger = logging.getLogger("creamcode.tools.registry")

    def register(self, tool: Tool, handler: Callable) -> None:
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler
        self._logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        if name in self._tools:
            del self._tools[name]
        if name in self._handlers:
            del self._handlers[name]
        self._logger.debug(f"Unregistered tool: {name}")

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_handler(self, name: str) -> Callable | None:
        return self._handlers.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    async def call_tool(
        self,
        name: str,
        arguments: dict,
        tool_call_id: str,
    ) -> ToolResult:
        if name not in self._tools or name not in self._handlers:
            raise ToolNotFoundError(f"Tool '{name}' not found")

        await self._event_bus.publish(Event(
            name="tool.called",
            source="tool_system",
            data={"name": name, "arguments": arguments, "tool_call_id": tool_call_id}
        ))

        handler = self._handlers[name]
        try:
            result = await handler(**arguments)
            content = str(result)
            is_error = False
        except Exception as e:
            content = str(e)
            is_error = True
            self._logger.error(f"Tool '{name}' execution failed: {e}", exc_info=True)

        await self._event_bus.publish(Event(
            name="tool.result",
            source="tool_system",
            data={"name": name, "result": content, "tool_call_id": tool_call_id, "is_error": is_error}
        ))

        return ToolResult(
            tool_call_id=tool_call_id,
            content=content,
            is_error=is_error
        )

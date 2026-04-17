from __future__ import annotations

import asyncio
import pytest

from creamcode.core.event_bus import EventBus
from creamcode.types import Tool, Event
from creamcode.tools.registry import ToolRegistry, ToolNotFoundError
from creamcode.tools.decorator import tool, set_global_registry


class TestToolRegistryBasic:
    def test_initial_state(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        assert registry.list_tools() == []

    def test_register_tool(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="test", description="A test tool", parameters={})

        async def handler():
            return "result"

        registry.register(tool_def, handler)
        assert registry.has_tool("test")
        assert registry.get_tool("test") == tool_def

    def test_unregister_tool(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="test", description="A test tool", parameters={})

        async def handler():
            return "result"

        registry.register(tool_def, handler)
        registry.unregister("test")
        assert not registry.has_tool("test")
        assert registry.get_tool("test") is None

    def test_list_tools(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool1 = Tool(name="tool1", description="Tool 1", parameters={})
        tool2 = Tool(name="tool2", description="Tool 2", parameters={})

        async def handler1():
            return "result1"

        async def handler2():
            return "result2"

        registry.register(tool1, handler1)
        registry.register(tool2, handler2)
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools


class TestToolDecorator:
    def test_tool_decorator_registers(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)

        @tool(name="decorated", description="A decorated tool")
        async def my_tool() -> str:
            return "done"

        assert registry.has_tool("decorated")
        tool_def = registry.get_tool("decorated")
        assert tool_def.name == "decorated"
        assert tool_def.description == "A decorated tool"
        set_global_registry(None)

    def test_tool_decorator_default_name(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)

        @tool(description="A decorated tool")
        async def my_tool() -> str:
            return "done"

        assert registry.has_tool("my_tool")
        set_global_registry(None)


class TestToolCall:
    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="echo", description="Echo input", parameters={})

        async def handler(message: str) -> str:
            return f"echo: {message}"

        registry.register(tool_def, handler)
        result = await registry.call_tool("echo", {"message": "hello"}, "call_1")
        assert result.tool_call_id == "call_1"
        assert result.content == "echo: hello"
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        with pytest.raises(ToolNotFoundError):
            await registry.call_tool("nonexistent", {}, "call_1")

    @pytest.mark.asyncio
    async def test_call_tool_error(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="fail", description="Failing tool", parameters={})

        async def handler():
            raise RuntimeError("Tool failed")

        registry.register(tool_def, handler)
        result = await registry.call_tool("fail", {}, "call_1")
        assert result.is_error
        assert "Tool failed" in result.content


class TestToolEvents:
    @pytest.mark.asyncio
    async def test_tool_called_event(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="test", description="Test tool", parameters={})

        async def handler():
            return "result"

        registry.register(tool_def, handler)

        called_event = None

        async def capture_called(event: Event):
            nonlocal called_event
            called_event = event

        await bus.subscribe("tool.called", capture_called)
        await registry.call_tool("test", {}, "call_1")

        assert called_event is not None
        assert called_event.name == "tool.called"
        assert called_event.data["name"] == "test"
        assert called_event.data["tool_call_id"] == "call_1"

    @pytest.mark.asyncio
    async def test_tool_result_event(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="test", description="Test tool", parameters={})

        async def handler():
            return "result"

        registry.register(tool_def, handler)

        result_event = None

        async def capture_result(event: Event):
            nonlocal result_event
            result_event = event

        await bus.subscribe("tool.result", capture_result)
        await registry.call_tool("test", {}, "call_1")

        assert result_event is not None
        assert result_event.name == "tool.result"
        assert result_event.data["result"] == "result"
        assert result_event.data["tool_call_id"] == "call_1"


class TestToolConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        bus = EventBus()
        registry = ToolRegistry(bus)
        tool_def = Tool(name="delay", description="Delayed tool", parameters={})
        results = []

        async def handler(value: int) -> str:
            await asyncio.sleep(0.01)
            return f"value: {value}"

        registry.register(tool_def, handler)

        async def call_tool(i: int):
            result = await registry.call_tool("delay", {"value": i}, f"call_{i}")
            results.append(result)

        await asyncio.gather(*[call_tool(i) for i in range(10)])
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result.content == f"value: {i}"

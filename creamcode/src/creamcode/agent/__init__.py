from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..types import Message, Response, Event
from ..core.event_bus import EventBus
from ..adapters.base import BaseAdapter
from ..tools.registry import ToolRegistry
from ..memory.context import ContextWindowManager


class AgentError(Exception):
    """Agent 相关错误"""
    pass


class BaseAgent(ABC):
    """
    Agent 抽象基类
    
    Agent 负责：
    1. 协调对话流程
    2. 选择合适的适配器
    3. 管理工具调用
    4. 处理记忆
    """

    def __init__(
        self,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        context_manager: ContextWindowManager,
    ):
        self.event_bus = event_bus
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self._adapter: BaseAdapter | None = None

    @abstractmethod
    async def process(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ) -> Response:
        """
        处理用户消息并返回响应
        """
        pass

    @abstractmethod
    async def stream_process(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ):
        """
        流式处理用户消息
        """
        pass

    def set_adapter(self, adapter: BaseAdapter) -> None:
        """设置使用的适配器"""
        self._adapter = adapter

    @property
    def adapter(self) -> BaseAdapter | None:
        """获取当前适配器"""
        return self._adapter


class DefaultAgent(BaseAgent):
    """
    默认 Agent 实现
    
    处理流程：
    1. 准备消息上下文
    2. 发送到适配器
    3. 处理工具调用
    4. 返回响应
    """

    def __init__(
        self,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        context_manager: ContextWindowManager,
    ):
        super().__init__(event_bus, tool_registry, context_manager)
        self._max_turns: int = 10

    @property
    def max_turns(self) -> int:
        return self._max_turns

    @max_turns.setter
    def max_turns(self, value: int) -> None:
        self._max_turns = value

    async def process(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ) -> Response:
        if self._adapter is None:
            raise AgentError("No adapter configured")

        await self.event_bus.publish(Event(
            name="agent.start",
            source="agent",
            data={"user_message": user_message}
        ))

        messages = await self.context_manager.prepare_messages(
            system_prompt=system_prompt,
            query=user_message,
        )

        from ..types import Message, MessageRole
        messages.append(Message(role=MessageRole.USER, content=user_message))

        response = await self._send_with_tools(messages)

        await self.event_bus.publish(Event(
            name="agent.complete",
            source="agent",
            data={"response": response.content if response else ""}
        ))

        return response

    async def _send_with_tools(self, messages: list[Message]) -> Response:
        """Send messages with tool handling loop"""
        if self._adapter is None:
            raise AgentError("No adapter configured")

        tools = self.tool_registry.list_tools()
        turn = 0

        while turn < self._max_turns:
            response = await self._adapter.send_messages(messages, tools)

            if not response.tool_calls:
                return response

            for tool_call in response.tool_calls:
                result = await self.tool_registry.call_tool(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    tool_call_id=tool_call.id,
                )

                messages.append(Message(
                    role=MessageRole.TOOL,
                    content=result.content,
                    tool_call_id=tool_call.id,
                ))

            turn += 1

        raise AgentError(f"Max turns ({self._max_turns}) exceeded")

    async def stream_process(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ):
        if self._adapter is None:
            raise AgentError("No adapter configured")

        messages = await self.context_manager.prepare_messages(
            system_prompt=system_prompt,
            query=user_message,
        )

        from ..types import Message, MessageRole
        messages.append(Message(role=MessageRole.USER, content=user_message))

        tools = self.tool_registry.list_tools()

        async for chunk in self._adapter.stream_messages(messages, tools):
            yield chunk

            if chunk.tool_call:
                result = await self.tool_registry.call_tool(
                    name=chunk.tool_call.name,
                    arguments=chunk.tool_call.arguments,
                    tool_call_id=chunk.tool_call.id,
                )

                messages.append(Message(
                    role=MessageRole.TOOL,
                    content=result.content,
                    tool_call_id=chunk.tool_call.id,
                ))

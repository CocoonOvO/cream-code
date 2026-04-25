from __future__ import annotations

from typing import Optional
from ..types import Message, TokenUsage, Event
from ..core.event_bus import EventBus


class WorkingMemory:
    """
    工作记忆：当前会话消息
    实现 Token 限制和智能截断
    """

    def __init__(
        self,
        max_tokens: int = 100000,
        reserved_tokens: int = 4096,
    ):
        self._messages: list[Message] = []
        self.max_tokens = max_tokens
        self.reserved_tokens = reserved_tokens
        self._current_usage = TokenUsage(input_tokens=0, output_tokens=0)

    @property
    def messages(self) -> list[Message]:
        """获取当前消息列表"""
        return self._messages.copy()

    @property
    def usage(self) -> TokenUsage:
        """获取当前 Token 使用量"""
        return self._current_usage

    def add(self, message: Message) -> None:
        """添加消息"""
        self._messages.append(message)

    def get_context(self) -> list[Message]:
        """获取当前上下文（可能已被截断）"""
        return self._messages.copy()

    def get_token_count(self, messages: list[Message]) -> int:
        """估算消息列表的 Token 数量"""
        return sum(self.estimate_tokens(msg.content) for msg in messages)

    def estimate_tokens(self, text: str) -> int:
        """简单估算：中文约 2 token/字符，英文约 4 token/词"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other = len(text) - chinese_chars
        return chinese_chars // 2 + other // 4

    def truncate(self, max_tokens: int) -> list[Message]:
        """
        截断消息以适应 Token 限制
        优先级：系统提示 > 最近消息 > 早期消息
        """
        if not self._messages:
            return []

        system_messages = [m for m in self._messages if m.role.value == "system"]
        non_system_messages = [m for m in self._messages if m.role.value != "system"]

        current_tokens = self.get_token_count(non_system_messages)
        result = system_messages.copy()

        if current_tokens <= max_tokens:
            result.extend(non_system_messages)
            return result

        result.extend(non_system_messages)
        total_tokens = self.get_token_count(result)

        while total_tokens > max_tokens and len(result) > len(system_messages):
            removed = result.pop(len(system_messages))
            total_tokens -= self.estimate_tokens(removed.content)

        return result

    def clear(self) -> None:
        """清空工作记忆"""
        self._messages.clear()

    async def on_before_send(
        self,
        event_bus: EventBus,
        short_term_summary: Optional[str] = None,
    ) -> list[Message]:
        """
        发送消息前的处理
        1. 如果 Token 超限，先触发短期记忆更新
        2. 然后截断
        3. 返回准备好的消息列表
        """
        available_tokens = self.max_tokens - self.reserved_tokens
        current_tokens = self.get_token_count(self._messages)

        if current_tokens > available_tokens:
            await event_bus.publish(Event(
                name="memory.short_term.update",
                source="memory_system",
                data={"summary": short_term_summary}
            ))

            truncated = self.truncate(available_tokens)
            token_count = self.get_token_count(truncated)

            await event_bus.publish(Event(
                name="memory.working.updated",
                source="memory_system",
                data={"message_count": len(truncated), "tokens": token_count}
            ))

            return truncated

        await event_bus.publish(Event(
            name="memory.working.updated",
            source="memory_system",
            data={"message_count": len(self._messages), "tokens": current_tokens}
        ))

        return self._messages.copy()

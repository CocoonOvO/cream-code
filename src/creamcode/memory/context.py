from typing import List, Optional

from ..types import Message, MessageRole, Response, Event
from .working import WorkingMemory
from .short_term import ShortTermMemory
from .long_term import LongTermMemory, DreamContext
from ..core.event_bus import EventBus


class ContextWindowManager:
    """
    上下文窗口管理器
    整合工作记忆、短期记忆、长期记忆，准备发送给 AI 的消息列表
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        short_term_memory: ShortTermMemory,
        long_term_memory: LongTermMemory,
        event_bus: EventBus,
    ):
        self.working = working_memory
        self.short_term = short_term_memory
        self.long_term = long_term_memory
        self.event_bus = event_bus
        self._max_context_tokens: int = 100000

    @property
    def max_context_tokens(self) -> int:
        return self._max_context_tokens

    @max_context_tokens.setter
    def max_context_tokens(self, value: int):
        self._max_context_tokens = value

    async def prepare_messages(
        self,
        system_prompt: str | None = None,
        query: str | None = None,
    ) -> List[Message]:
        """
        准备发送给 AI 的消息列表
        
        1. 从长期记忆获取相关主题
        2. 拼接短期记忆摘要
        3. 拼接工作记忆消息
        4. 按 token 限制截断
        5. 添加系统提示（如有）
        
        Returns:
            准备好的消息列表
        """
        messages: List[Message] = []

        if system_prompt:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=system_prompt
            ))

        if query:
            relevant_topics = await self.long_term.retrieve(query, limit=3)
            if relevant_topics:
                topic_content = "\n".join([
                    f"- {t.name}: {t.content}" 
                    for t in relevant_topics
                ])
                messages.append(Message(
                    role=MessageRole.SYSTEM,
                    content=f"相关记忆:\n{topic_content}"
                ))

        recent_context = await self.short_term.get_recent_context(limit=3)
        if recent_context:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=f"近期对话摘要:\n{recent_context}"
            ))

        working_messages = self.working.get_context()
        messages.extend(working_messages)

        total_tokens = self.working.get_token_count(messages)
        if total_tokens > self._max_context_tokens:
            reserved = self._max_context_tokens - self.working.reserved_tokens
            truncated = self.working.truncate(reserved)
            messages = [
                m for m in messages 
                if m.role == MessageRole.SYSTEM
            ]
            messages.extend(truncated)

        return messages

    async def on_before_agent_call(
        self,
        system_prompt: str | None = None,
    ) -> List[Message]:
        """
        Agent 调用前的处理
        检查是否需要触发短期记忆更新
        """
        current_tokens = self.working.get_token_count(self.working.messages)
        available_tokens = self._max_context_tokens - self.working.reserved_tokens

        if current_tokens > available_tokens:
            await self.event_bus.publish(Event(
                name="memory.short_term.update",
                source="memory_system",
                data={}
            ))

        return await self.prepare_messages(system_prompt=system_prompt)

    async def on_after_agent_response(
        self,
        response: Response,
    ) -> None:
        """
        Agent 响应后的处理
        """
        pass

    async def on_session_end(self) -> None:
        """
        会话结束时的处理
        1. 生成短期记忆摘要
        2. 增加长期记忆会话计数
        3. 检查是否需要触发 Dream
        """
        messages = self.working.messages
        summary = await self.short_term.generate_summary(messages)
        await self.short_term.add_summary(summary)

        self.long_term.increment_session_count()

        if self.long_term.can_trigger_dream():
            await self.long_term.dream(
                self.event_bus,
                DreamContext(
                    recent_summaries=self.short_term.summaries,
                    current_topics=list(self.long_term.topics.keys()),
                    memory_state={}
                )
            )

        await self.event_bus.publish(Event(
            name="memory.session_end",
            source="memory_system",
            data={"summary_id": summary.id}
        ))

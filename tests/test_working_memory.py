from __future__ import annotations

import pytest
from creamcode.memory import WorkingMemory
from creamcode.types import Message, MessageRole, TokenUsage, Event
from creamcode.core.event_bus import EventBus


class TestWorkingMemoryBasic:
    def test_initial_state(self):
        wm = WorkingMemory()
        assert wm.messages == []
        assert wm.usage.input_tokens == 0
        assert wm.usage.output_tokens == 0
        assert wm.max_tokens == 100000
        assert wm.reserved_tokens == 4096

    def test_custom_limits(self):
        wm = WorkingMemory(max_tokens=50000, reserved_tokens=2048)
        assert wm.max_tokens == 50000
        assert wm.reserved_tokens == 2048

    def test_add_message(self):
        wm = WorkingMemory()
        msg = Message(role=MessageRole.USER, content="Hello")
        wm.add(msg)
        assert len(wm.messages) == 1
        assert wm.messages[0].content == "Hello"

    def test_messages_returns_copy(self):
        wm = WorkingMemory()
        msg = Message(role=MessageRole.USER, content="Hello")
        wm.add(msg)
        messages = wm.messages
        messages.append(Message(role=MessageRole.USER, content="World"))
        assert len(wm.messages) == 1

    def test_clear(self):
        wm = WorkingMemory()
        wm.add(Message(role=MessageRole.USER, content="Hello"))
        wm.add(Message(role=MessageRole.ASSISTANT, content="Hi"))
        wm.clear()
        assert wm.messages == []


class TestTokenEstimation:
    def test_chinese_token_estimation(self):
        wm = WorkingMemory()
        chinese_text = "你好世界"
        tokens = wm.estimate_tokens(chinese_text)
        assert tokens == 2

    def test_english_token_estimation(self):
        wm = WorkingMemory()
        english_text = "hello world"
        tokens = wm.estimate_tokens(english_text)
        assert tokens == 2

    def test_mixed_token_estimation(self):
        wm = WorkingMemory()
        mixed_text = "你好 hello 世界 world"
        tokens = wm.estimate_tokens(mixed_text)
        assert tokens == 5

    def test_empty_text(self):
        wm = WorkingMemory()
        assert wm.estimate_tokens("") == 0

    def test_get_token_count_empty(self):
        wm = WorkingMemory()
        assert wm.get_token_count([]) == 0

    def test_get_token_count_multiple_messages(self):
        wm = WorkingMemory()
        messages = [
            Message(role=MessageRole.USER, content="你好"),
            Message(role=MessageRole.ASSISTANT, content="hello world"),
        ]
        count = wm.get_token_count(messages)
        assert count == 3


class TestTruncation:
    def test_truncate_empty(self):
        wm = WorkingMemory()
        result = wm.truncate(1000)
        assert result == []

    def test_truncate_preserves_system_message(self):
        wm = WorkingMemory(max_tokens=100)
        system_msg = Message(role=MessageRole.SYSTEM, content="You are a helpful assistant")
        user_msg = Message(role=MessageRole.USER, content="Hello")
        wm.add(system_msg)
        wm.add(user_msg)

        result = wm.truncate(10)
        system_count = sum(1 for m in result if m.role == MessageRole.SYSTEM)
        assert system_count == 1

    def test_truncate_preserves_recent_messages(self):
        wm = WorkingMemory(max_tokens=50)
        for i in range(10):
            wm.add(Message(role=MessageRole.USER, content=f"Message {i}"))

        result = wm.truncate(5)
        latest_content = result[-1].content if result else None
        assert latest_content == "Message 9"

    def test_truncate_removes_early_messages(self):
        wm = WorkingMemory(max_tokens=50)
        for i in range(10):
            wm.add(Message(role=MessageRole.USER, content="Hello"))

        result = wm.truncate(5)
        assert len(result) < 10

    def test_truncate_with_system_and_conversation(self):
        wm = WorkingMemory(max_tokens=50)
        wm.add(Message(role=MessageRole.SYSTEM, content="System prompt"))
        for i in range(5):
            wm.add(Message(role=MessageRole.USER, content=f"User message {i}"))
            wm.add(Message(role=MessageRole.ASSISTANT, content=f"Assistant reply {i}"))

        result = wm.truncate(10)
        assert any(m.role == MessageRole.SYSTEM for m in result)


class TestOnBeforeSend:
    @pytest.mark.asyncio
    async def test_on_before_send_within_limit(self):
        wm = WorkingMemory(max_tokens=100000, reserved_tokens=4096)
        wm.add(Message(role=MessageRole.USER, content="Hello"))
        bus = EventBus()

        result = await wm.on_before_send(bus)

        assert len(result) == 1
        assert result[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_on_before_send_triggers_short_term_update(self):
        wm = WorkingMemory(max_tokens=100, reserved_tokens=50)
        for i in range(10):
            wm.add(Message(role=MessageRole.USER, content="A" * 100))

        bus = EventBus()
        update_called = []

        async def handler(event: Event):
            update_called.append(event.name)

        await bus.subscribe("memory.short_term.update", handler)
        await wm.on_before_send(bus, short_term_summary="test summary")

        assert "memory.short_term.update" in update_called

    @pytest.mark.asyncio
    async def test_on_before_send_publishes_updated_event(self):
        wm = WorkingMemory(max_tokens=100000, reserved_tokens=4096)
        wm.add(Message(role=MessageRole.USER, content="Hello"))
        bus = EventBus()
        updated_events = []

        async def handler(event: Event):
            updated_events.append(event)

        await bus.subscribe("memory.working.updated", handler)
        await wm.on_before_send(bus)

        assert len(updated_events) == 1
        assert updated_events[0].data["message_count"] == 1

    @pytest.mark.asyncio
    async def test_on_before_send_truncates_when_over_limit(self):
        wm = WorkingMemory(max_tokens=100, reserved_tokens=10)
        for i in range(20):
            wm.add(Message(role=MessageRole.USER, content="This is a long message"))

        bus = EventBus()
        result = await wm.on_before_send(bus)

        total_tokens = wm.get_token_count(result)
        assert total_tokens <= 90


class TestEdgeCases:
    def test_single_message(self):
        wm = WorkingMemory()
        msg = Message(role=MessageRole.USER, content="Hello")
        wm.add(msg)
        assert len(wm.messages) == 1
        assert wm.get_token_count(wm.messages) == 1

    def test_token_count_at_limit(self):
        wm = WorkingMemory(max_tokens=100, reserved_tokens=50)
        available = wm.max_tokens - wm.reserved_tokens
        assert available == 50

    def test_get_context_returns_copy(self):
        wm = WorkingMemory()
        wm.add(Message(role=MessageRole.USER, content="Hello"))
        context1 = wm.get_context()
        context2 = wm.get_context()
        assert context1 == context2
        assert context1 is not context2

    @pytest.mark.asyncio
    async def test_empty_memory_on_before_send(self):
        wm = WorkingMemory()
        bus = EventBus()
        result = await wm.on_before_send(bus)
        assert result == []

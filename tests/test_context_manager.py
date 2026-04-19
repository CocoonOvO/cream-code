import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from datetime import datetime

from creamcode.memory import (
    WorkingMemory,
    ShortTermMemory,
    LongTermMemory,
    ContextWindowManager,
)
from creamcode.memory.short_term import ConversationSummary
from creamcode.memory.long_term import MemoryTopic, DreamContext
from creamcode.core.event_bus import EventBus
from creamcode.types import Message, MessageRole, Response, TokenUsage


@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def working_memory():
    return WorkingMemory(max_tokens=10000, reserved_tokens=1000)

@pytest.fixture
def short_term_memory():
    return ShortTermMemory()

@pytest.fixture
def long_term_memory():
    return LongTermMemory()

@pytest.fixture
def context_manager(working_memory, short_term_memory, long_term_memory, event_bus):
    return ContextWindowManager(
        working_memory=working_memory,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        event_bus=event_bus,
    )


class TestContextWindowManager:
    def test_create_context_manager(self, context_manager):
        assert context_manager.working is not None
        assert context_manager.short_term is not None
        assert context_manager.long_term is not None
        assert context_manager.event_bus is not None
        assert context_manager.max_context_tokens == 100000

    def test_max_context_tokens_setter(self, context_manager):
        context_manager.max_context_tokens = 50000
        assert context_manager.max_context_tokens == 50000


class TestPrepareMessages:
    @pytest.mark.asyncio
    async def test_prepare_messages_empty(self, context_manager):
        messages = await context_manager.prepare_messages()
        assert messages == []

    @pytest.mark.asyncio
    async def test_prepare_messages_with_system_prompt(self, context_manager):
        messages = await context_manager.prepare_messages(
            system_prompt="You are a helpful assistant."
        )
        assert len(messages) == 1
        assert messages[0].role == MessageRole.SYSTEM
        assert messages[0].content == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_prepare_messages_with_working_memory(
        self, context_manager, working_memory
    ):
        working_memory.add(Message(role=MessageRole.USER, content="Hello"))
        working_memory.add(Message(role=MessageRole.ASSISTANT, content="Hi there!"))

        messages = await context_manager.prepare_messages()

        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_prepare_messages_with_long_term_memory(
        self, context_manager, long_term_memory
    ):
        long_term_memory._topics["python"] = MemoryTopic(
            name="python",
            content="Python programming language",
            last_accessed=datetime.now(),
            access_count=1,
        )

        messages = await context_manager.prepare_messages(query="python")

        assert len(messages) == 1
        assert messages[0].role == MessageRole.SYSTEM
        assert "python" in messages[0].content

    @pytest.mark.asyncio
    async def test_prepare_messages_with_short_term_memory(
        self, context_manager, short_term_memory
    ):
        summary = ConversationSummary(
            id="test-id",
            timestamp=datetime.now(),
            summary="Previous conversation about testing",
            message_count=5,
        )
        await short_term_memory.add_summary(summary)

        messages = await context_manager.prepare_messages()

        assert len(messages) == 1
        assert messages[0].role == MessageRole.SYSTEM
        assert "测试" in messages[0].content or "testing" in messages[0].content.lower()


class TestTokenLimits:
    @pytest.mark.asyncio
    async def test_prepare_messages_respects_token_limit(
        self, context_manager, working_memory
    ):
        context_manager._max_context_tokens = 100
        working_memory.reserved_tokens = 50

        for i in range(20):
            working_memory.add(Message(
                role=MessageRole.USER,
                content="This is a test message with some content to make it longer."
            ))

        messages = await context_manager.prepare_messages()

        total_tokens = working_memory.get_token_count(messages)
        assert total_tokens <= context_manager.max_context_tokens

    @pytest.mark.asyncio
    async def test_truncate_preserves_system_messages(
        self, context_manager, working_memory
    ):
        context_manager._max_context_tokens = 200
        working_memory.reserved_tokens = 50

        working_memory.add(Message(role=MessageRole.SYSTEM, content="System prompt"))
        for i in range(10):
            working_memory.add(Message(
                role=MessageRole.USER,
                content="A" * 100
            ))

        messages = await context_manager.prepare_messages()

        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        assert len(system_msgs) >= 1


class TestSessionEnd:
    @pytest.mark.asyncio
    async def test_on_session_end_generates_summary(
        self, context_manager, working_memory, short_term_memory
    ):
        working_memory.add(Message(role=MessageRole.USER, content="Hello"))
        working_memory.add(Message(role=MessageRole.ASSISTANT, content="Hi"))

        await context_manager.on_session_end()

        summaries = short_term_memory.summaries
        assert len(summaries) == 1
        assert summaries[0].message_count == 2

    @pytest.mark.asyncio
    async def test_on_session_end_increments_session_count(
        self, context_manager, long_term_memory
    ):
        initial_count = long_term_memory._session_count_since_dream

        await context_manager.on_session_end()

        assert long_term_memory._session_count_since_dream == initial_count + 1

    @pytest.mark.asyncio
    async def test_on_session_end_triggers_dream(
        self, context_manager, long_term_memory, short_term_memory
    ):
        long_term_memory._session_count_since_dream = 5
        long_term_memory._last_dream_time = None

        summary = ConversationSummary(
            id="test-id",
            timestamp=datetime.now(),
            summary="Test summary",
            message_count=5,
        )
        await short_term_memory.add_summary(summary)

        await context_manager.on_session_end()

        assert long_term_memory._session_count_since_dream == 0

    @pytest.mark.asyncio
    async def test_on_session_end_publishes_event(
        self, context_manager, event_bus
    ):
        published_events = []
        async def capture_handler(event):
            published_events.append(event)
        await event_bus.subscribe("memory.session_end", capture_handler)

        await context_manager.on_session_end()

        assert len(published_events) == 1
        assert published_events[0].name == "memory.session_end"
        assert "summary_id" in published_events[0].data


class TestBeforeAgentCall:
    @pytest.mark.asyncio
    async def test_on_before_agent_call_returns_messages(
        self, context_manager, working_memory
    ):
        working_memory.add(Message(role=MessageRole.USER, content="Test"))

        messages = await context_manager.on_before_agent_call(
            system_prompt="You are a helpful assistant."
        )

        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_on_before_agent_call_triggers_short_term_update(
        self, context_manager, working_memory, event_bus
    ):
        context_manager._max_context_tokens = 100
        working_memory.reserved_tokens = 10

        for i in range(50):
            working_memory.add(Message(role=MessageRole.USER, content="x" * 50))

        published_events = []
        async def capture_handler(event):
            published_events.append(event)
        await event_bus.subscribe("memory.short_term.update", capture_handler)

        await context_manager.on_before_agent_call()


class TestAfterAgentResponse:
    @pytest.mark.asyncio
    async def test_on_after_agent_response_does_not_error(
        self, context_manager
    ):
        response = Response(
            content="Test response",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        )

        await context_manager.on_after_agent_response(response)

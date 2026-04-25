from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from creamcode.memory import ShortTermMemory, ConversationSummary
from creamcode.types import Message, MessageRole, Event
from creamcode.core.event_bus import EventBus


class TestShortTermMemoryBasic:
    def test_initial_state(self):
        stm = ShortTermMemory()
        assert stm.summaries == []
        assert stm.max_summaries == 10

    def test_custom_max_summaries(self):
        stm = ShortTermMemory(max_summaries=5)
        assert stm.max_summaries == 5

    def test_summaries_returns_copy(self):
        stm = ShortTermMemory()
        stm._summaries.append(
            ConversationSummary(
                id="1",
                timestamp=datetime.now(),
                summary="test",
                message_count=1,
            )
        )
        summaries = stm.summaries
        summaries.append(
            ConversationSummary(
                id="2",
                timestamp=datetime.now(),
                summary="test2",
                message_count=2,
            )
        )
        assert len(stm.summaries) == 1


class TestConversationSummary:
    def test_to_dict(self):
        summary = ConversationSummary(
            id="test-id",
            timestamp=datetime(2026, 4, 15, 10, 0, 0),
            summary="Test summary",
            message_count=5,
            topics=["python", "web"],
            keywords=["fastapi", "async"],
        )
        data = summary.to_dict()
        
        assert data["id"] == "test-id"
        assert data["timestamp"] == "2026-04-15T10:00:00"
        assert data["summary"] == "Test summary"
        assert data["message_count"] == 5
        assert data["topics"] == ["python", "web"]
        assert data["keywords"] == ["fastapi", "async"]

    def test_from_dict(self):
        data = {
            "id": "test-id",
            "timestamp": "2026-04-15T10:00:00",
            "summary": "Test summary",
            "message_count": 5,
            "topics": ["python"],
            "keywords": ["fastapi"],
        }
        summary = ConversationSummary.from_dict(data)
        
        assert summary.id == "test-id"
        assert summary.summary == "Test summary"
        assert summary.message_count == 5


class TestAddSummary:
    @pytest.mark.asyncio
    async def test_add_summary(self):
        stm = ShortTermMemory()
        summary = ConversationSummary(
            id="1",
            timestamp=datetime.now(),
            summary="Test summary",
            message_count=5,
        )
        await stm.add_summary(summary)
        
        assert len(stm.summaries) == 1
        assert stm.summaries[0].id == "1"

    @pytest.mark.asyncio
    async def test_add_summary_removes_oldest_when_over_limit(self):
        stm = ShortTermMemory(max_summaries=3)
        
        for i in range(5):
            summary = ConversationSummary(
                id=f"summary-{i}",
                timestamp=datetime.now(),
                summary=f"Summary {i}",
                message_count=i,
            )
            await stm.add_summary(summary)
        
        assert len(stm.summaries) == 3
        assert stm.summaries[0].id == "summary-2"
        assert stm.summaries[2].id == "summary-4"


class TestGenerateSummary:
    @pytest.mark.asyncio
    async def test_generate_summary_empty_messages(self):
        stm = ShortTermMemory()
        summary = await stm.generate_summary([])
        
        assert summary.summary == ""

    @pytest.mark.asyncio
    async def test_generate_summary_with_messages(self):
        stm = ShortTermMemory()
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            Message(role=MessageRole.USER, content="How are you?"),
            Message(role=MessageRole.ASSISTANT, content="I'm fine, thanks!"),
        ]
        summary = await stm.generate_summary(messages)
        
        assert "2 条用户消息" in summary.summary
        assert "2 条助手回复" in summary.summary
        assert summary.message_count == 4
        assert summary.id

    @pytest.mark.asyncio
    async def test_generate_summary_with_topics(self):
        stm = ShortTermMemory()
        messages = [
            Message(role=MessageRole.USER, content="Tell me about Python"),
        ]
        summary = await stm.generate_summary(messages, topics=["programming", "python"])
        
        assert "programming" in summary.topics
        assert "python" in summary.topics


class TestGetRecentContext:
    @pytest.mark.asyncio
    async def test_get_recent_context_empty(self):
        stm = ShortTermMemory()
        context = await stm.get_recent_context()
        
        assert context == ""

    @pytest.mark.asyncio
    async def test_get_recent_context_with_summaries(self):
        stm = ShortTermMemory()
        
        for i in range(3):
            summary = ConversationSummary(
                id=f"summary-{i}",
                timestamp=datetime.now(),
                summary=f"Summary {i}",
                message_count=i + 1,
            )
            await stm.add_summary(summary)
        
        context = await stm.get_recent_context(limit=2)
        
        assert "Summary 1" in context
        assert "Summary 2" in context
        assert "Summary 0" not in context

    @pytest.mark.asyncio
    async def test_get_recent_context_respects_limit(self):
        stm = ShortTermMemory()
        
        for i in range(5):
            await stm.add_summary(
                ConversationSummary(
                    id=f"summary-{i}",
                    timestamp=datetime.now(),
                    summary=f"Summary {i}",
                    message_count=i,
                )
            )
        
        context = await stm.get_recent_context(limit=3)
        
        assert "Summary 2" in context
        assert "Summary 4" in context


class TestGetRelevantSummaries:
    @pytest.mark.asyncio
    async def test_get_relevant_summaries_empty(self):
        stm = ShortTermMemory()
        results = await stm.get_relevant_summaries("python")
        
        assert results == []

    @pytest.mark.asyncio
    async def test_get_relevant_summaries_by_keyword(self):
        stm = ShortTermMemory()
        
        await stm.add_summary(
            ConversationSummary(
                id="python-chat",
                timestamp=datetime.now(),
                summary="Discussed Python programming",
                message_count=5,
                keywords=["python", "fastapi"],
            )
        )
        await stm.add_summary(
            ConversationSummary(
                id="javascript-chat",
                timestamp=datetime.now(),
                summary="Discussed JavaScript",
                message_count=3,
                keywords=["javascript", "node"],
            )
        )
        
        results = await stm.get_relevant_summaries("python programming", limit=2)
        
        assert len(results) >= 1
        assert results[0].id == "python-chat"

    @pytest.mark.asyncio
    async def test_get_relevant_summaries_limit(self):
        stm = ShortTermMemory()
        
        for i in range(5):
            await stm.add_summary(
                ConversationSummary(
                    id=f"summary-{i}",
                    timestamp=datetime.now(),
                    summary=f"Summary about programming {i}",
                    message_count=3,
                    keywords=["programming"],
                )
            )
        
        results = await stm.get_relevant_summaries("programming", limit=2)
        
        assert len(results) == 2


class TestPersistence:
    @pytest.mark.asyncio
    async def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stm = ShortTermMemory(storage_dir=Path(tmpdir), max_summaries=5)
            
            for i in range(3):
                await stm.add_summary(
                    ConversationSummary(
                        id=f"summary-{i}",
                        timestamp=datetime.now(),
                        summary=f"Summary {i}",
                        message_count=i + 1,
                    )
                )
            
            await stm.save()
            
            new_stm = ShortTermMemory(storage_dir=Path(tmpdir), max_summaries=5)
            await new_stm.load()
            
            assert len(new_stm.summaries) == 3
            assert new_stm.summaries[0].id == "summary-0"
            assert new_stm.summaries[2].id == "summary-2"

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stm = ShortTermMemory(storage_dir=Path(tmpdir))
            await stm.load()
            
            assert stm.summaries == []


class TestOnSessionEnd:
    @pytest.mark.asyncio
    async def test_on_session_end_generates_and_stores_summary(self):
        stm = ShortTermMemory()
        bus = EventBus()
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi!"),
        ]
        
        summary = await stm.on_session_end(bus, messages)
        
        assert len(stm.summaries) == 1
        assert summary.message_count == 2
        assert summary.summary.count("1") >= 2

    @pytest.mark.asyncio
    async def test_on_session_end_publishes_event(self):
        stm = ShortTermMemory()
        bus = EventBus()
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]
        
        published_events = []
        
        async def handler(event: Event):
            published_events.append(event)
        
        await bus.subscribe("memory.short_term.updated", handler)
        
        await stm.on_session_end(bus, messages)
        
        assert len(published_events) == 1
        assert published_events[0].name == "memory.short_term.updated"
        assert published_events[0].data["summary_count"] == 1


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_generate_summary_with_no_content(self):
        stm = ShortTermMemory()
        messages = [
            Message(role=MessageRole.USER, content=""),
            Message(role=MessageRole.ASSISTANT, content=""),
        ]
        summary = await stm.generate_summary(messages)
        
        assert summary.summary == "会话包含 1 条用户消息，1 条助手回复。"

    @pytest.mark.asyncio
    async def test_multiple_summaries_order_preserved(self):
        stm = ShortTermMemory()
        
        for i in range(4):
            await stm.add_summary(
                ConversationSummary(
                    id=f"id-{i}",
                    timestamp=datetime.now(),
                    summary=f"Summary {i}",
                    message_count=i,
                )
            )
        
        assert [s.id for s in stm.summaries] == ["id-0", "id-1", "id-2", "id-3"]

    @pytest.mark.asyncio
    async def test_empty_keyword_extraction(self):
        stm = ShortTermMemory()
        messages = [
            Message(role=MessageRole.USER, content="Hi"),
            Message(role=MessageRole.ASSISTANT, content="Hello"),
        ]
        summary = await stm.generate_summary(messages)
        
        assert len(summary.keywords) <= 5

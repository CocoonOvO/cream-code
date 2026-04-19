import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from creamcode.memory.long_term import LongTermMemory, MemoryTopic, DreamContext
from creamcode.memory.short_term import ConversationSummary
from creamcode.core.event_bus import EventBus
from creamcode.types import Event


class TestMemoryTopic:
    def test_create_topic(self):
        topic = MemoryTopic(
            name="python",
            content="Python programming language",
            last_accessed=datetime.now(),
        )
        assert topic.name == "python"
        assert topic.access_count == 0
        assert topic.related_topics == []

    def test_topic_to_dict(self):
        now = datetime.now()
        topic = MemoryTopic(
            name="fastapi",
            content="FastAPI framework",
            last_accessed=now,
            access_count=3,
            related_topics=["python", "async"],
        )
        data = topic.to_dict()
        assert data["name"] == "fastapi"
        assert data["access_count"] == 3
        assert data["related_topics"] == ["python", "async"]

    def test_topic_from_dict(self):
        data = {
            "name": "docker",
            "content": "Container platform",
            "last_accessed": "2026-04-15T10:00:00",
            "access_count": 5,
            "related_topics": ["containers", "devops"],
        }
        topic = MemoryTopic.from_dict(data)
        assert topic.name == "docker"
        assert topic.access_count == 5
        assert "containers" in topic.related_topics


class TestLongTermMemory:
    @pytest.fixture
    def memory(self):
        return LongTermMemory(
            storage_dir=Path("~/.cache/test_creamcode/long_term"),
            time_gate_hours=24,
            session_gate=5,
        )

    @pytest.fixture
    def event_bus(self):
        return EventBus()

    def test_create_memory(self, memory):
        assert memory.topics == {}
        assert memory._session_count_since_dream == 0
        assert memory._dream_lock is False

    def test_increment_session_count(self, memory):
        memory.increment_session_count()
        assert memory._session_count_since_dream == 1
        memory.increment_session_count()
        assert memory._session_count_since_dream == 2

    def test_check_time_gate_first_time(self, memory):
        assert memory._check_time_gate() is True

    def test_check_time_gate_recent_dream(self, memory):
        memory._last_dream_time = datetime.now()
        assert memory._check_time_gate() is False

    def test_check_time_gate_old_dream(self, memory):
        memory._last_dream_time = datetime.now() - timedelta(hours=25)
        assert memory._check_time_gate() is True

    def test_check_session_gate_below_threshold(self, memory):
        memory._session_count_since_dream = 3
        assert memory._check_session_gate() is False

    def test_check_session_gate_at_threshold(self, memory):
        memory._session_count_since_dream = 5
        assert memory._check_session_gate() is True

    def test_check_lock_unlocked(self, memory):
        assert memory._check_lock() is True

    def test_check_lock_locked(self, memory):
        memory._dream_lock = True
        assert memory._check_lock() is False

    def test_can_trigger_dream_all_gates_pass(self, memory):
        memory._last_dream_time = datetime.now() - timedelta(hours=25)
        memory._session_count_since_dream = 5
        assert memory.can_trigger_dream() is True

    def test_can_trigger_dream_time_gate_fails(self, memory):
        memory._last_dream_time = datetime.now()
        memory._session_count_since_dream = 5
        assert memory.can_trigger_dream() is False

    def test_can_trigger_dream_session_gate_fails(self, memory):
        memory._last_dream_time = datetime.now() - timedelta(hours=25)
        memory._session_count_since_dream = 3
        assert memory.can_trigger_dream() is False

    def test_can_trigger_dream_lock_fails(self, memory):
        memory._last_dream_time = datetime.now() - timedelta(hours=25)
        memory._session_count_since_dream = 5
        memory._dream_lock = True
        assert memory.can_trigger_dream() is False

    def test_on_dream_complete(self, memory):
        memory._dream_lock = True
        memory._session_count_since_dream = 10
        memory._last_dream_time = None

        memory.on_dream_complete()

        assert memory._dream_lock is False
        assert memory._session_count_since_dream == 0
        assert memory._last_dream_time is not None

    @pytest.mark.asyncio
    async def test_dream_creates_topics(self, memory, event_bus):
        summaries = [
            ConversationSummary(
                id="1",
                timestamp=datetime.now(),
                summary="Used FastAPI to build an API",
                message_count=5,
                keywords=["fastapi", "api", "python"],
            ),
            ConversationSummary(
                id="2",
                timestamp=datetime.now(),
                summary="Working with Docker containers",
                message_count=3,
                keywords=["docker", "container"],
            ),
        ]
        context = DreamContext(
            recent_summaries=summaries,
            current_topics=[],
            memory_state={},
        )

        updated = await memory.dream(event_bus, context)

        assert "fastapi" in updated
        assert "python" in updated
        assert "docker" in updated
        assert "fastapi" in memory.topics

    @pytest.mark.asyncio
    async def test_dream_updates_existing_topics(self, memory, event_bus):
        memory._topics["python"] = MemoryTopic(
            name="python",
            content="Python programming",
            last_accessed=datetime.now() - timedelta(days=1),
            access_count=3,
        )

        summaries = [
            ConversationSummary(
                id="1",
                timestamp=datetime.now(),
                summary="Learning Python async",
                message_count=5,
                keywords=["python", "async"],
            ),
        ]
        context = DreamContext(
            recent_summaries=summaries,
            current_topics=[],
            memory_state={},
        )

        await memory.dream(event_bus, context)

        assert memory._topics["python"].access_count == 4

    @pytest.mark.asyncio
    async def test_dream_resets_state(self, memory, event_bus):
        memory._dream_lock = True
        memory._session_count_since_dream = 10

        summaries = [
            ConversationSummary(
                id="1",
                timestamp=datetime.now(),
                summary="Test session",
                message_count=2,
                keywords=["test"],
            ),
        ]
        context = DreamContext(
            recent_summaries=summaries,
            current_topics=[],
            memory_state={},
        )

        await memory.dream(event_bus, context)

        assert memory._dream_lock is False
        assert memory._session_count_since_dream == 0

    @pytest.mark.asyncio
    async def test_dream_publishes_event(self, memory, event_bus):
        published_events = []
        original_publish = event_bus.publish

        async def mock_publish(event):
            published_events.append(event)

        event_bus.publish = mock_publish

        summaries = [
            ConversationSummary(
                id="1",
                timestamp=datetime.now(),
                summary="Test",
                message_count=1,
                keywords=["test"],
            ),
        ]
        context = DreamContext(
            recent_summaries=summaries,
            current_topics=[],
            memory_state={},
        )

        await memory.dream(event_bus, context)

        assert len(published_events) == 1
        assert published_events[0].name == "memory.long_term.dream_complete"

    @pytest.mark.asyncio
    async def test_consolidate(self, memory, event_bus):
        summaries = [
            ConversationSummary(
                id="1",
                timestamp=datetime.now(),
                summary="Docker setup",
                message_count=3,
                keywords=["docker"],
            ),
        ]

        updated = await memory.consolidate(event_bus, summaries)

        assert "docker" in updated
        assert memory._dream_lock is False

    @pytest.mark.asyncio
    async def test_retrieve(self, memory):
        memory._topics["python"] = MemoryTopic(
            name="python",
            content="Python programming language",
            last_accessed=datetime.now(),
            access_count=5,
        )
        memory._topics["fastapi"] = MemoryTopic(
            name="fastapi",
            content="FastAPI web framework",
            last_accessed=datetime.now(),
            access_count=3,
            related_topics=["python"],
        )
        memory._topics["docker"] = MemoryTopic(
            name="docker",
            content="Container platform",
            last_accessed=datetime.now(),
            access_count=2,
        )

        results = await memory.retrieve("python fastapi", limit=2)

        assert len(results) <= 2
        topic_names = [t.name for t in results]
        assert "python" in topic_names
        assert "fastapi" in topic_names

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self, memory):
        memory._topics["python"] = MemoryTopic(
            name="python",
            content="Python",
            last_accessed=datetime.now(),
        )

        results = await memory.retrieve("", limit=5)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_save_and_load(self, memory):
        memory._topics["python"] = MemoryTopic(
            name="python",
            content="Python programming",
            last_accessed=datetime.now(),
            access_count=5,
            related_topics=["fastapi"],
        )
        memory._last_dream_time = datetime.now() - timedelta(hours=1)
        memory._session_count_since_dream = 3

        await memory.save()

        new_memory = LongTermMemory(storage_dir=memory.storage_dir)
        await new_memory.load()

        assert "python" in new_memory.topics
        assert new_memory.topics["python"].content == "Python programming"
        assert new_memory.topics["python"].access_count == 5

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, memory):
        memory.storage_dir = Path("~/.cache/nonexistent_test")
        await memory.load()

        assert memory.topics == {}

    def test_topics_property_returns_copy(self, memory):
        memory._topics["python"] = MemoryTopic(
            name="python",
            content="Python",
            last_accessed=datetime.now(),
        )

        topics = memory.topics
        topics["python"] = None

        assert memory._topics["python"] is not None

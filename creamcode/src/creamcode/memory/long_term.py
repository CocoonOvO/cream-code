from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
from collections import Counter

from ..types import Event
from ..core.event_bus import EventBus
from .short_term import ConversationSummary


@dataclass
class MemoryTopic:
    """记忆主题"""
    name: str
    content: str
    last_accessed: datetime
    access_count: int = 0
    related_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "content": self.content,
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "related_topics": self.related_topics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryTopic:
        return cls(
            name=data["name"],
            content=data["content"],
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
            related_topics=data.get("related_topics", []),
        )


@dataclass
class DreamContext:
    """Dream 上下文"""
    recent_summaries: list[ConversationSummary]
    current_topics: list[str]
    memory_state: dict


class LongTermMemory:
    """
    长期记忆：通过 Dream 整理的持久化记忆
    实现三门触发机制
    """

    def __init__(
        self,
        storage_dir: Path | None = None,
        time_gate_hours: int = 24,
        session_gate: int = 5,
    ):
        self._topics: dict[str, MemoryTopic] = {}
        self.storage_dir = storage_dir or Path("~/.cache/creamcode/memory/long_term")
        self.time_gate_hours = time_gate_hours
        self.session_gate = session_gate
        self._last_dream_time: datetime | None = None
        self._session_count_since_dream: int = 0
        self._dream_lock: bool = False

    @property
    def topics(self) -> dict[str, MemoryTopic]:
        """获取所有主题"""
        return self._topics.copy()

    def _check_time_gate(self) -> bool:
        """检查时间门"""
        if self._last_dream_time is None:
            return True
        elapsed = datetime.now() - self._last_dream_time
        return elapsed >= timedelta(hours=self.time_gate_hours)

    def _check_session_gate(self) -> bool:
        """检查会话数门"""
        return self._session_count_since_dream >= self.session_gate

    def _check_lock(self) -> bool:
        """检查锁门（防止并发 Dream）"""
        return not self._dream_lock

    def can_trigger_dream(self) -> bool:
        """检查是否可以触发 Dream"""
        return (
            self._check_time_gate() and
            self._check_session_gate() and
            self._check_lock()
        )

    def _extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """从文本中提取关键词"""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        word_freq = Counter(words)
        return [word for word, _ in word_freq.most_common(top_n)]

    def _find_related_topics(self, keywords: list[str]) -> list[str]:
        """找出与关键词相关的主题"""
        related = []
        for keyword in keywords:
            for topic_name, topic in self._topics.items():
                if keyword in topic.related_topics or topic.name in keyword:
                    related.append(topic_name)
        return list(set(related))

    async def dream(
        self,
        event_bus: EventBus,
        context: DreamContext,
    ) -> list[str]:
        """
        Dream 整理逻辑
        1. 获取整理锁
        2. 分析最近的短期记忆摘要
        3. 提取主题和关系
        4. 更新长期记忆
        5. 释放锁
        返回更新的主题列表
        """
        self._dream_lock = True

        try:
            all_content = "\n".join([
                s.summary for s in context.recent_summaries
            ])
            all_keywords: list[str] = []
            for summary in context.recent_summaries:
                all_keywords.extend(summary.keywords)
            all_keywords = list(set(all_keywords))

            if not all_keywords:
                all_keywords = self._extract_keywords(all_content)

            updated_topics: list[str] = []
            for keyword in all_keywords:
                if keyword in self._topics:
                    self._topics[keyword].access_count += 1
                    self._topics[keyword].last_accessed = datetime.now()
                    existing_related = set(self._topics[keyword].related_topics)
                    new_related = self._find_related_topics([keyword])
                    self._topics[keyword].related_topics = list(existing_related | set(new_related))
                else:
                    related = self._find_related_topics([keyword])
                    self._topics[keyword] = MemoryTopic(
                        name=keyword,
                        content=f"关于 {keyword} 的记忆",
                        last_accessed=datetime.now(),
                        access_count=1,
                        related_topics=related,
                    )
                updated_topics.append(keyword)

            for topic in context.current_topics:
                if topic not in updated_topics:
                    updated_topics.append(topic)

            await event_bus.publish(Event(
                name="memory.long_term.dream_complete",
                source="memory_system",
                data={"topics_updated": updated_topics}
            ))

            return updated_topics

        finally:
            self.on_dream_complete()

    async def consolidate(
        self,
        event_bus: EventBus,
        summaries: list[ConversationSummary],
    ) -> list[str]:
        """
        整合新记忆到长期记忆
        """
        context = DreamContext(
            recent_summaries=summaries,
            current_topics=list(self._topics.keys()),
            memory_state={}
        )
        return await self.dream(event_bus, context)

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
    ) -> list[MemoryTopic]:
        """
        检索相关记忆
        """
        query_words = set(self._extract_keywords(query.lower()))

        scored: list[tuple[int, MemoryTopic]] = []
        for topic in self._topics.values():
            score = 0
            if topic.name in query_words:
                score += 5
            if any(word in query_words for word in topic.related_topics):
                score += 3
            if any(word in topic.content.lower() for word in query_words):
                score += 1
            score += min(topic.access_count, 5)
            scored.append((score, topic))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [topic for _, topic in scored[:limit]]

    async def save(self) -> None:
        """保存到磁盘"""
        storage_path = self.storage_dir.expanduser()
        storage_path.mkdir(parents=True, exist_ok=True)

        data = {
            "topics": {name: topic.to_dict() for name, topic in self._topics.items()},
            "last_dream_time": self._last_dream_time.isoformat() if self._last_dream_time else None,
            "session_count_since_dream": self._session_count_since_dream,
        }

        file_path = storage_path / "long_term_memory.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def load(self) -> None:
        """从磁盘加载"""
        file_path = self.storage_dir.expanduser() / "long_term_memory.json"

        if not file_path.exists():
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._topics = {
            name: MemoryTopic.from_dict(topic_data)
            for name, topic_data in data.get("topics", {}).items()
        }

        last_dream_time = data.get("last_dream_time")
        if last_dream_time:
            self._last_dream_time = datetime.fromisoformat(last_dream_time)
        self._session_count_since_dream = data.get("session_count_since_dream", 0)

    def increment_session_count(self) -> None:
        """增加会话计数"""
        self._session_count_since_dream += 1

    def on_dream_complete(self) -> None:
        """Dream 完成后调用"""
        self._last_dream_time = datetime.now()
        self._session_count_since_dream = 0
        self._dream_lock = False

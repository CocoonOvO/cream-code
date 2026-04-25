from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
import re
import uuid

from ..types import Message, MessageRole, Event
from ..core.event_bus import EventBus


@dataclass
class ConversationSummary:
    """会话摘要"""
    id: str
    timestamp: datetime
    summary: str
    message_count: int
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "message_count": self.message_count,
            "topics": self.topics,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConversationSummary:
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            summary=data["summary"],
            message_count=data["message_count"],
            topics=data.get("topics", []),
            keywords=data.get("keywords", []),
        )


class ShortTermMemory:
    """
    短期记忆：最近对话的摘要
    在会话结束时生成摘要
    """

    def __init__(
        self,
        storage_dir: Path | None = None,
        max_summaries: int = 10,
    ):
        self._summaries: list[ConversationSummary] = []
        self.storage_dir = storage_dir or Path("~/.cache/creamcode/memory/short_term")
        self.max_summaries = max_summaries

    @property
    def summaries(self) -> list[ConversationSummary]:
        """获取所有摘要"""
        return self._summaries.copy()

    async def generate_summary(
        self,
        messages: list[Message],
        topics: list[str] | None = None,
    ) -> ConversationSummary:
        """
        从消息列表生成摘要
        使用 LLM 或简单规则生成
        """
        summary_text = await self._create_simple_summary(messages)
        keywords = self._extract_keywords(messages)
        
        summary = ConversationSummary(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            summary=summary_text,
            message_count=len(messages),
            topics=topics or [],
            keywords=keywords,
        )
        return summary

    async def _create_simple_summary(self, messages: list[Message]) -> str:
        """简单摘要：提取关键词和高亮消息"""
        if not messages:
            return ""

        user_msgs = [m for m in messages if m.role == MessageRole.USER]
        assistant_msgs = [m for m in messages if m.role == MessageRole.ASSISTANT]

        summary = f"会话包含 {len(user_msgs)} 条用户消息，{len(assistant_msgs)} 条助手回复。"

        for msg in reversed(assistant_msgs):
            if msg.content:
                content_preview = msg.content[:200]
                if len(msg.content) > 200:
                    content_preview += "..."
                summary += f"\n最后回复：{content_preview}"
                break

        return summary

    def _extract_keywords(self, messages: list[Message]) -> list[str]:
        """从消息中提取关键词"""
        all_text = " ".join(m.content for m in messages if m.content)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
        
        word_freq = Counter(words)
        keywords = [word for word, _ in word_freq.most_common(5)]
        return keywords

    async def add_summary(self, summary: ConversationSummary) -> None:
        """
        添加摘要
        超出数量限制时移除最旧的
        """
        self._summaries.append(summary)
        
        while len(self._summaries) > self.max_summaries:
            self._summaries.pop(0)

    async def get_recent_context(self, limit: int = 5) -> str:
        """
        获取最近 N 个摘要的上下文
        """
        recent = self._summaries[-limit:] if self._summaries else []
        
        if not recent:
            return ""
        
        context_parts = []
        for i, s in enumerate(recent, 1):
            context_parts.append(f"[会话 {i}]\n{s.summary}")
        
        return "\n\n".join(context_parts)

    async def get_relevant_summaries(
        self,
        query: str,
        limit: int = 3,
    ) -> list[ConversationSummary]:
        """
        获取与查询相关的摘要
        """
        query_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', query.lower()))
        
        scored = []
        for summary in self._summaries:
            score = 0
            summary_words = set(k.lower() for k in summary.keywords)
            score += len(query_words & summary_words) * 2
            
            if any(word in summary.summary.lower() for word in query_words):
                score += 1
            
            scored.append((score, summary))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [s for _, s in scored[:limit]]

    async def save(self) -> None:
        """保存到磁盘"""
        storage_path = self.storage_dir.expanduser()
        storage_path.mkdir(parents=True, exist_ok=True)
        
        file_path = storage_path / "summaries.json"
        data = [s.to_dict() for s in self._summaries]
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def load(self) -> None:
        """从磁盘加载"""
        file_path = self.storage_dir.expanduser() / "summaries.json"
        
        if not file_path.exists():
            return
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self._summaries = [ConversationSummary.from_dict(d) for d in data]

    async def on_session_end(
        self,
        event_bus: EventBus,
        messages: list[Message],
    ) -> ConversationSummary:
        """
        会话结束时调用
        1. 生成摘要
        2. 保存到列表
        3. 发布事件
        """
        summary = await self.generate_summary(messages)
        await self.add_summary(summary)
        
        await event_bus.publish(Event(
            name="memory.short_term.updated",
            source="memory_system",
            data={"summary_count": len(self._summaries)}
        ))
        
        return summary

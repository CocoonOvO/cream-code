import asyncio
from typing import Callable, Awaitable, Any
from dataclasses import dataclass, field
from asyncio import Lock
import logging

from ..types import Event


Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    事件总线 - 插件间通信核心
    提供事件的发布/订阅机制
    """

    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = {}
        self._lock = Lock()
        self._logger = logging.getLogger("creamcode.event_bus")

    async def publish(self, event: Event) -> None:
        """
        发布事件
        所有订阅该事件的处理器都会被调用
        """
        handlers = self.get_handlers(event.name)
        self._logger.debug(
            f"Publishing event '{event.name}' from '{event.source}' to {len(handlers)} handler(s)"
        )

        if not handlers:
            return

        async def safe_call(handler: Handler) -> None:
            try:
                await handler(event)
            except Exception as e:
                self._logger.error(
                    f"Handler error for event '{event.name}': {e}", exc_info=True
                )

        await asyncio.gather(*[safe_call(h) for h in handlers])

    async def subscribe(self, event_name: str, handler: Handler) -> None:
        """
        订阅事件
        """
        async with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            if handler not in self._subscribers[event_name]:
                self._subscribers[event_name].append(handler)

    async def unsubscribe(self, event_name: str, handler: Handler) -> None:
        """
        取消订阅
        """
        async with self._lock:
            if event_name in self._subscribers:
                if handler in self._subscribers[event_name]:
                    self._subscribers[event_name].remove(handler)
                if not self._subscribers[event_name]:
                    del self._subscribers[event_name]

    def get_handlers(self, event_name: str) -> list[Handler]:
        """获取事件的所有处理器"""
        handlers = self._subscribers.get(event_name, []).copy()
        if event_name != "*":
            handlers.extend(self._subscribers.get("*", []))
        return handlers

    def list_subscriptions(self, source: str | None = None) -> list[str]:
        """
        列出所有订阅
        如果指定 source，则只列出该源的订阅
        """
        return list(self._subscribers.keys())

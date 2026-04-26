from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable


class Event:
    """事件对象 - 可变，插件链式处理"""

    name: str
    data: dict[str, Any]
    metadata: dict[str, Any]

    def __init__(self, name: str, data: dict = None, metadata: dict = None):
        self.name = name
        self.data = data or {}
        self.metadata = metadata or {}

    def with_data(self, **kwargs) -> Event:
        return Event(self.name, {**self.data, **kwargs}, self.metadata)

    def with_metadata(self, **kwargs) -> Event:
        return Event(self.name, self.data, {**self.metadata, **kwargs})


EventHandler = Callable[[Event], Awaitable[Event | None]]


class EventSpace:
    """事件空间，如 app、session"""

    def __init__(self, name: str, event_bus: EventBus):
        self.space_name = name
        self._event_bus = event_bus

    def event(self, sub_name: str, priority: int = 0):
        """发射事件装饰器，如 @app.event("starting")"""
        full_name = f"{self.space_name}.{sub_name}"
        return self._event_bus._emit_decorator(full_name, priority)

    def path(self, sub_name: str) -> str:
        """获取完整路径"""
        return f"{self.space_name}.{sub_name}"


class EventBus:
    """事件总线 - 单例模式"""

    _instance: EventBus | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: dict[str, list[tuple[int, EventHandler]]] = {}
            cls._instance.event_spaces: dict[str, EventSpace] = {}
        return cls._instance

    def create_space(self, name: str) -> EventSpace:
        """创建事件空间"""
        if name in self.event_spaces:
            return self.event_spaces[name]
        space = EventSpace(name, self)
        self.event_spaces[name] = space
        return space

    def get_space(self, name: str) -> EventSpace | None:
        """获取事件空间"""
        return self.event_spaces.get(name)

    def on(self, event_path: str, priority: int = 0):
        """订阅装饰器，如 @event_bus.on("app.starting")"""
        def decorator(func: EventHandler):
            self.subscribe(event_path, func, priority)
            return func
        return decorator

    subscribe = on

    def subscribe(self, event_path: str, handler: EventHandler, priority: int = 0) -> None:
        if event_path not in self._handlers:
            self._handlers[event_path] = []
        self._handlers[event_path].append((priority, handler))
        self._handlers[event_path].sort(key=lambda x: x[0])

    def unsubscribe(self, event_path: str, handler: EventHandler) -> None:
        if event_path in self._handlers:
            self._handlers[event_path] = [
                (p, h) for p, h in self._handlers[event_path] if h != handler
            ]

    async def publish(self, event: Event) -> Event | None:
        handlers = self._handlers.get(event.name, [])
        result = event
        for _, handler in handlers:
            result = await handler(result)
            if result is None:
                return None
        return result

    def _emit_decorator(self, event_name: str, priority: int = 0):
        """发射装饰器工厂"""

        def decorator(func):
            @wraps(func)
            async def wrapper(self, *args, **kwargs):
                eb = getattr(self, "event_bus", None) or event_bus
                result = await func(self, *args, **kwargs)
                await eb.publish(Event(event_name))
                return result

            return wrapper

        return decorator


event_bus = EventBus()
on = event_bus.on

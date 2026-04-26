from __future__ import annotations

from abc import ABC
from typing import Any

from ..core.event_bus import event_bus as _event_bus, on as _on


class CoreEvents:
    """核心事件常量表 - 仅开发时参考，运行时无作用"""

    APP_STARTING = "app.starting"
    APP_STARTED = "app.started"
    APP_SHUTDOWN = "app.shutdown"
    APP_STOPPED = "app.stopped"

    SESSION_START = "session.start"
    SESSION_END = "session.end"

    MESSAGE_INCOMING = "message.incoming"
    MESSAGE_OUTGOING = "message.outgoing"
    MESSAGE_PROCESSED = "message.processed"

    AGENT_THINKING = "agent.thinking"
    AGENT_PROMPT = "agent.prompt"
    AGENT_RESPONSE = "agent.response"
    AGENT_RESULT = "agent.result"

    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"

    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_UNLOADED = "plugin.unloaded"


class ServiceRegistry:
    """服务注册表"""

    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        self._services[name] = service

    def get(self, name: str) -> Any | None:
        return self._services.get(name)

    def list_services(self) -> list[str]:
        return list(self._services.keys())


class PluginContext:
    """插件上下文"""

    def __init__(
        self,
        event_bus: Any,
        config: dict[str, Any],
        services: ServiceRegistry,
    ):
        self.event_bus = event_bus
        self.config = config
        self.services = services


class Plugin(ABC):
    """插件基类"""

    name: str = ""
    version: str = "0.1.0"
    priority: int = 0
    depends_on: list[str] = []

    _context: PluginContext | None = None
    _enabled: bool = False

    async def on_load(self, context: PluginContext) -> None:
        self._context = context

    async def on_enable(self) -> None:
        self._enabled = True

    async def on_disable(self) -> None:
        self._enabled = False

    async def on_unload(self) -> None:
        self._enabled = False
        self._context = None

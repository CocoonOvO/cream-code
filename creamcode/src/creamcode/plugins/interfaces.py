from __future__ import annotations


class CoreEvents:
    """核心事件常量表 - 仅开发时参考"""

    LIFECYCLE_START = "lifecycle.start"
    LIFECYCLE_STOP = "lifecycle.stop"

    PLUGIN_LOAD = "plugin.load"
    PLUGIN_UNLOAD = "plugin.unload"
    PLUGIN_ENABLE = "plugin.enable"
    PLUGIN_DISABLE = "plugin.disable"

    CLI_START = "cli.start"
    CLI_COMMAND = "cli.command"
    CLI_INTERACTIVE = "cli.interactive"

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


class ServiceRegistry:
    """服务注册表"""

    def __init__(self):
        self._services: dict[str, object] = {}

    def register(self, name: str, service: object) -> None:
        self._services[name] = service

    def get(self, name: str) -> object | None:
        return self._services.get(name)

    def list_services(self) -> list[str]:
        return list(self._services.keys())


class PluginContext:
    """插件上下文"""

    def __init__(
        self,
        event_bus: object,
        config: dict,
        services: ServiceRegistry,
    ):
        self.event_bus = event_bus
        self.config = config
        self.services = services

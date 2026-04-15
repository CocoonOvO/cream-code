from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import re


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    metadata: dict | None = None


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str | None = None
    required: bool = False
    default: Any = None


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    anthropic_schema: dict | None = None
    openai_function: dict | None = None
    metadata: dict | None = None


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False
    metadata: dict | None = None


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int = field(init=False)

    def __post_init__(self):
        self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class Response:
    content: str
    tool_calls: list[ToolCall] | None = None
    usage: TokenUsage | None = None
    model: str | None = None
    stop_reason: str | None = None


@dataclass
class ResponseChunk:
    content: str
    tool_call: ToolCall | None = None
    is_final: bool = False


@dataclass
class Event:
    name: str
    source: str
    data: dict

    def __post_init__(self):
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', self.name):
            raise ValueError(f"Invalid event name: {self.name}")


class PluginType(str, Enum):
    SYSTEM = "system"
    USER = "user"


@dataclass
class PluginMetadata:
    name: str
    version: str
    type: PluginType
    depends_on: list[str] = field(default_factory=list)
    description: str | None = None


@dataclass
class CommandInfo:
    namespace: str
    name: str
    handler_path: str
    description: str | None = None


class LifecycleState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class AdapterErrorCode(str, Enum):
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    CONTEXT_LENGTH = "context_length"
    MODEL_NOT_FOUND = "model_not_found"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


class AdapterError(Exception):
    def __init__(
        self,
        code: AdapterErrorCode,
        message: str,
        retryable: bool = False,
        details: dict | None = None
    ):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    retryable_codes: set[str] = field(default_factory=lambda: {
        "rate_limit", "timeout", "server_error"
    })

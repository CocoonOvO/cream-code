from __future__ import annotations

import pytest
from creamcode.types import (
    AdapterError,
    AdapterErrorCode,
    CommandInfo,
    Event,
    LifecycleState,
    Message,
    MessageRole,
    PluginMetadata,
    PluginType,
    Response,
    ResponseChunk,
    RetryConfig,
    Tool,
    ToolCall,
    ToolParameter,
    ToolResult,
    TokenUsage,
)


class TestMessageRole:
    def test_roles_exist(self):
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.TOOL == "tool"


class TestMessage:
    def test_create_user_message(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_call_id is None
        assert msg.tool_calls is None
        assert msg.metadata is None

    def test_create_system_message(self):
        msg = Message(role=MessageRole.SYSTEM, content="You are helpful")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are helpful"

    def test_create_assistant_message(self):
        msg = Message(role=MessageRole.ASSISTANT, content="I can help")
        assert msg.role == MessageRole.ASSISTANT

    def test_create_tool_message(self):
        msg = Message(
            role=MessageRole.TOOL,
            content="tool result",
            name="get_weather",
            tool_call_id="call_123"
        )
        assert msg.role == MessageRole.TOOL
        assert msg.name == "get_weather"
        assert msg.tool_call_id == "call_123"

    def test_create_message_with_tool_calls(self):
        tool_call = ToolCall(id="call_1", name="test_tool", arguments={"arg": "value"})
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Using tool",
            tool_calls=[tool_call]
        )
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call_1"

    def test_create_message_with_metadata(self):
        msg = Message(
            role=MessageRole.USER,
            content="Hello",
            metadata={"key": "value"}
        )
        assert msg.metadata == {"key": "value"}

    def test_message_serialization(self):
        msg = Message(role=MessageRole.USER, content="Test")
        serialized = {
            "role": msg.role,
            "content": msg.content,
            "name": msg.name,
            "tool_call_id": msg.tool_call_id,
            "tool_calls": msg.tool_calls,
            "metadata": msg.metadata
        }
        assert serialized["role"] == "user"
        assert serialized["content"] == "Test"

    def test_message_deserialization(self):
        data = {
            "role": "user",
            "content": "Hello",
            "name": None,
            "tool_call_id": None,
            "tool_calls": None,
            "metadata": None
        }
        msg = Message(**data)
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"


class TestToolCall:
    def test_create_tool_call(self):
        tc = ToolCall(id="call_1", name="get_weather", arguments={"city": "NYC"})
        assert tc.id == "call_1"
        assert tc.name == "get_weather"
        assert tc.arguments == {"city": "NYC"}

    def test_tool_call_arguments_is_dict(self):
        tc = ToolCall(id="call_1", name="test", arguments={})
        assert isinstance(tc.arguments, dict)

    def test_tool_call_with_complex_arguments(self):
        tc = ToolCall(
            id="call_2",
            name="search",
            arguments={"query": "test", "limit": 10, "filters": {"type": "article"}}
        )
        assert tc.arguments["query"] == "test"
        assert tc.arguments["limit"] == 10
        assert tc.arguments["filters"] == {"type": "article"}


class TestToolParameter:
    def test_create_required_parameter(self):
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True

    def test_create_optional_parameter_with_default(self):
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Result limit",
            required=False,
            default=10
        )
        assert param.required is False
        assert param.default == 10


class TestTool:
    def test_create_tool_with_json_schema(self):
        params = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
        tool = Tool(
            name="search",
            description="Search the web",
            parameters=params
        )
        assert tool.name == "search"
        assert tool.parameters["type"] == "object"

    def test_create_tool_with_anthropic_schema(self):
        anthropic_schema = {
            "name": "get_weather",
            "description": "Get weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                }
            }
        }
        tool = Tool(
            name="get_weather",
            description="Get weather",
            parameters={},
            anthropic_schema=anthropic_schema
        )
        assert tool.anthropic_schema is not None
        assert tool.anthropic_schema["name"] == "get_weather"

    def test_create_tool_with_openai_function(self):
        openai_fn = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        }
        tool = Tool(
            name="get_weather",
            description="Get weather",
            parameters={},
            openai_function=openai_fn
        )
        assert tool.openai_function is not None

    def test_create_tool_with_metadata(self):
        tool = Tool(
            name="test",
            description="Test tool",
            parameters={},
            metadata={"version": "1.0", "author": "test"}
        )
        assert tool.metadata["version"] == "1.0"


class TestToolResult:
    def test_create_tool_result(self):
        result = ToolResult(tool_call_id="call_1", content="result content")
        assert result.tool_call_id == "call_1"
        assert result.content == "result content"
        assert result.is_error is False

    def test_create_error_result(self):
        result = ToolResult(
            tool_call_id="call_1",
            content="Error occurred",
            is_error=True
        )
        assert result.is_error is True

    def test_tool_result_with_metadata(self):
        result = ToolResult(
            tool_call_id="call_1",
            content="ok",
            metadata={"timestamp": "2024-01-01"}
        )
        assert result.metadata["timestamp"] == "2024-01-01"


class TestTokenUsage:
    def test_create_token_usage(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_total_tokens_calculation(self):
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        assert usage.total_tokens == usage.input_tokens + usage.output_tokens

    def test_zero_tokens(self):
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        assert usage.total_tokens == 0


class TestResponse:
    def test_create_response(self):
        resp = Response(content="Hello, how can I help?")
        assert resp.content == "Hello, how can I help?"
        assert resp.tool_calls is None
        assert resp.usage is None

    def test_create_response_with_usage(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        resp = Response(content="Answer", usage=usage)
        assert resp.usage.total_tokens == 150

    def test_create_response_with_tool_calls(self):
        tc = ToolCall(id="call_1", name="test", arguments={})
        resp = Response(content="Using tool", tool_calls=[tc])
        assert resp.tool_calls is not None
        assert len(resp.tool_calls) == 1

    def test_response_with_model_and_stop_reason(self):
        resp = Response(
            content="Response",
            model="gpt-4",
            stop_reason="end_turn"
        )
        assert resp.model == "gpt-4"
        assert resp.stop_reason == "end_turn"


class TestResponseChunk:
    def test_create_response_chunk(self):
        chunk = ResponseChunk(content="Hello")
        assert chunk.content == "Hello"
        assert chunk.tool_call is None
        assert chunk.is_final is False

    def test_create_final_chunk(self):
        chunk = ResponseChunk(content="final", is_final=True)
        assert chunk.is_final is True

    def test_chunk_with_tool_call_delta(self):
        tc = ToolCall(id="call_1", name="test", arguments={})
        chunk = ResponseChunk(content="", tool_call=tc)
        assert chunk.tool_call is not None


class TestEvent:
    def test_create_event(self):
        event = Event(name="tool_called", source="test_plugin", data={"tool": "test"})
        assert event.name == "tool_called"
        assert event.source == "test_plugin"
        assert event.data["tool"] == "test"

    def test_valid_event_names(self):
        event = Event(name="myEvent123", source="plugin", data={})
        assert event.name == "myEvent123"

        event2 = Event(name="test_event", source="plugin", data={})
        assert event2.name == "test_event"

    def test_event_names_are_flexible(self):
        # Event names are flexible - no validation restrictions
        # Numbers at start
        e1 = Event(name="123invalid", source="plugin", data={})
        assert e1.name == "123invalid"

        # Dots (common for namespaced events like plugin.loaded)
        e2 = Event(name="plugin.loaded", source="plugin", data={})
        assert e2.name == "plugin.loaded"

        # Hyphens
        e3 = Event(name="invalid-name", source="plugin", data={})
        assert e3.name == "invalid-name"

        # Spaces
        e4 = Event(name="invalid name", source="plugin", data={})
        assert e4.name == "invalid name"


class TestPluginType:
    def test_plugin_types(self):
        assert PluginType.SYSTEM == "system"
        assert PluginType.USER == "user"


class TestPluginMetadata:
    def test_create_system_plugin(self):
        meta = PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            type=PluginType.SYSTEM
        )
        assert meta.name == "my_plugin"
        assert meta.type == PluginType.SYSTEM

    def test_create_user_plugin(self):
        meta = PluginMetadata(
            name="user_plugin",
            version="0.1.0",
            type=PluginType.USER,
            description="A user plugin"
        )
        assert meta.type == PluginType.USER
        assert meta.description == "A user plugin"

    def test_plugin_with_dependencies(self):
        meta = PluginMetadata(
            name="dependent_plugin",
            version="1.0.0",
            type=PluginType.USER,
            depends_on=["plugin_a", "plugin_b"]
        )
        assert len(meta.depends_on) == 2
        assert "plugin_a" in meta.depends_on
        assert "plugin_b" in meta.depends_on

    def test_default_empty_depends_on(self):
        meta = PluginMetadata(
            name="standalone",
            version="1.0.0",
            type=PluginType.SYSTEM
        )
        assert meta.depends_on == []


class TestCommandInfo:
    def test_create_command_info(self):
        cmd = CommandInfo(
            namespace="my_plugin",
            name="hello",
            handler_path="my_plugin.hello"
        )
        assert cmd.namespace == "my_plugin"
        assert cmd.name == "hello"
        assert cmd.handler_path == "my_plugin.hello"

    def test_command_with_description(self):
        cmd = CommandInfo(
            namespace="test",
            name="cmd",
            handler_path="test.cmd",
            description="Test command"
        )
        assert cmd.description == "Test command"


class TestLifecycleState:
    def test_lifecycle_states(self):
        assert LifecycleState.STOPPED == "stopped"
        assert LifecycleState.STARTING == "starting"
        assert LifecycleState.RUNNING == "running"
        assert LifecycleState.STOPPING == "stopping"


class TestAdapterErrorCode:
    def test_error_codes(self):
        assert AdapterErrorCode.RATE_LIMIT == "rate_limit"
        assert AdapterErrorCode.AUTH == "auth"
        assert AdapterErrorCode.CONTEXT_LENGTH == "context_length"
        assert AdapterErrorCode.MODEL_NOT_FOUND == "model_not_found"
        assert AdapterErrorCode.TIMEOUT == "timeout"
        assert AdapterErrorCode.SERVER_ERROR == "server_error"
        assert AdapterErrorCode.UNKNOWN == "unknown"


class TestAdapterError:
    def test_create_error(self):
        err = AdapterError(
            code=AdapterErrorCode.RATE_LIMIT,
            message="Rate limit exceeded"
        )
        assert err.code == AdapterErrorCode.RATE_LIMIT
        assert err.message == "Rate limit exceeded"
        assert err.retryable is False
        assert err.details == {}

    def test_retryable_error(self):
        err = AdapterError(
            code=AdapterErrorCode.TIMEOUT,
            message="Request timed out",
            retryable=True
        )
        assert err.retryable is True

    def test_error_with_details(self):
        err = AdapterError(
            code=AdapterErrorCode.AUTH,
            message="Auth failed",
            details={"token": "expired"}
        )
        assert err.details["token"] == "expired"

    def test_error_is_exception(self):
        err = AdapterError(
            code=AdapterErrorCode.UNKNOWN,
            message="Unknown error"
        )
        with pytest.raises(AdapterError) as exc_info:
            raise err
        assert "Unknown error" in str(exc_info.value)

    def test_catch_adapter_error(self):
        err = AdapterError(
            code=AdapterErrorCode.SERVER_ERROR,
            message="Server error",
            retryable=True
        )
        try:
            raise err
        except AdapterError as caught:
            assert caught.code == AdapterErrorCode.SERVER_ERROR
            assert caught.retryable is True


class TestRetryConfig:
    def test_default_retry_config(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert "rate_limit" in config.retryable_codes
        assert "timeout" in config.retryable_codes
        assert "server_error" in config.retryable_codes

    def test_custom_retry_config(self):
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0

    def test_custom_retryable_codes(self):
        config = RetryConfig(
            retryable_codes={"rate_limit", "auth"}
        )
        assert "rate_limit" in config.retryable_codes
        assert "auth" in config.retryable_codes
        assert "timeout" not in config.retryable_codes

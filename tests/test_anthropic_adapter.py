from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import anthropic
from anthropic._exceptions import APIStatusError

from creamcode.adapters import AnthropicAdapter
from creamcode.core.event_bus import EventBus
from creamcode.types import (
    AdapterError,
    AdapterErrorCode,
    Message,
    MessageRole,
    Response,
    ResponseChunk,
    Tool,
    ToolCall,
    TokenUsage,
)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_api_key():
    return "test-api-key"


@pytest.fixture
def adapter(event_bus, mock_api_key):
    return AnthropicAdapter(
        api_key=mock_api_key,
        event_bus=event_bus,
        model="claude-sonnet-4-20250514",
    )


class TestAnthropicAdapterBasic:
    def test_adapter_name(self, adapter):
        assert adapter.name == "anthropic"

    def test_adapter_supported_models(self, adapter):
        models = adapter.supported_models
        assert "claude-opus-4-20250514" in models
        assert "claude-sonnet-4-20250514" in models
        assert "claude-haiku-4-20250507" in models

    def test_adapter_has_send_messages(self, adapter):
        import inspect
        assert inspect.iscoroutinefunction(adapter.send_messages)

    def test_adapter_has_stream_messages(self, adapter):
        import inspect
        assert inspect.isasyncgenfunction(adapter.stream_messages)


class TestMessageConversion:
    def test_convert_user_message(self):
        event_bus = EventBus()
        adapter = AnthropicAdapter(api_key="key", event_bus=event_bus)
        message = Message(role=MessageRole.USER, content="Hello")
        result = adapter._convert_message(message)
        assert result == {"role": "user", "content": "Hello"}

    def test_convert_assistant_message(self):
        event_bus = EventBus()
        adapter = AnthropicAdapter(api_key="key", event_bus=event_bus)
        message = Message(role=MessageRole.ASSISTANT, content="Hi there")
        result = adapter._convert_message(message)
        assert result == {"role": "assistant", "content": "Hi there"}

    def test_convert_system_message(self):
        event_bus = EventBus()
        adapter = AnthropicAdapter(api_key="key", event_bus=event_bus)
        message = Message(role=MessageRole.SYSTEM, content="You are helpful")
        result = adapter._convert_message(message)
        assert result == {"role": "user", "content": "[System] You are helpful"}

    def test_convert_tool_message(self):
        event_bus = EventBus()
        adapter = AnthropicAdapter(api_key="key", event_bus=event_bus)
        message = Message(
            role=MessageRole.TOOL,
            content="tool result content",
            tool_call_id="tool_1",
        )
        result = adapter._convert_message(message)
        assert result["role"] == "user"
        assert result["content"] == "tool result content"

    def test_convert_tool_message_with_tool_calls(self):
        event_bus = EventBus()
        adapter = AnthropicAdapter(api_key="key", event_bus=event_bus)
        tool_calls = [
            ToolCall(id="tool_1", name="bash", arguments={"command": "ls"})
        ]
        message = Message(
            role=MessageRole.TOOL,
            content="",
            tool_calls=tool_calls,
        )
        result = adapter._convert_message(message)
        assert result["role"] == "user"
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "tool_use"
        assert result["content"][0]["name"] == "bash"


class TestToolConversion:
    def test_convert_tools_with_anthropic_schema(self):
        tools = [
            Tool(
                name="get_weather",
                description="Get weather",
                parameters={},
                anthropic_schema={
                    "name": "get_weather",
                    "description": "Get weather",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        }
                    }
                }
            )
        ]
        from creamcode.adapters import convert_tools_for_anthropic
        result = convert_tools_for_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"

    def test_convert_tools_without_schema(self):
        tools = [
            Tool(
                name="bash",
                description="Execute command",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"}
                    }
                }
            )
        ]
        from creamcode.adapters import convert_tools_for_anthropic
        result = convert_tools_for_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "bash"
        assert result[0]["input_schema"]["properties"]["command"]["type"] == "string"


class TestMockApiCalls:
    @pytest.fixture
    def mock_client(self):
        with patch.object(anthropic.Anthropic, 'messages') as mock_messages:
            yield mock_messages

    @pytest.mark.asyncio
    async def test_send_messages_success(self, adapter, mock_client):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello!")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.create.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = await adapter.send_messages(messages)

        assert result.content == "Hello!"
        assert result.model == "claude-sonnet-4-20250514"
        assert result.stop_reason == "end_turn"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20

    @pytest.mark.asyncio
    async def test_send_messages_with_tool_calls(self, adapter, mock_client):
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "tool_1"
        mock_tool_block.name = "bash"
        mock_tool_block.input = {"command": "ls"}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "tool_use"
        mock_client.create.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Run ls")]
        result = await adapter.send_messages(messages)

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tool_1"
        assert result.tool_calls[0].name == "bash"
        assert result.tool_calls[0].arguments == {"command": "ls"}

    @pytest.mark.asyncio
    async def test_send_messages_with_tools(self, adapter, mock_client):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Done")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 10
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_client.create.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Use tool")]
        tools = [Tool(
            name="bash",
            description="Run command",
            parameters={"type": "object", "properties": {"command": {"type": "string"}}}
        )]
        result = await adapter.send_messages(messages, tools=tools)

        assert result.content == "Done"
        mock_client.create.assert_called_once()
        call_kwargs = mock_client.create.call_args.kwargs
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) == 1


def make_api_status_error(error_class, message):
    mock_response = MagicMock()
    mock_response.status_code = 400
    return error_class(message=message, response=mock_response, body=None)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_bad_request_error_maps_to_context_length(self, adapter):
        with patch.object(anthropic.Anthropic, 'messages') as mock_messages:
            mock_messages.create.side_effect = make_api_status_error(
                anthropic.BadRequestError, "context length exceeded"
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.CONTEXT_LENGTH
            assert not exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_auth_error_maps_to_auth(self, adapter):
        with patch.object(anthropic.Anthropic, 'messages') as mock_messages:
            mock_messages.create.side_effect = make_api_status_error(
                anthropic.AuthenticationError, "invalid api key"
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.AUTH
            assert not exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_retryable(self, adapter):
        with patch.object(anthropic.Anthropic, 'messages') as mock_messages:
            mock_messages.create.side_effect = make_api_status_error(
                anthropic.RateLimitError, "rate limited"
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.RATE_LIMIT
            assert exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_api_error_maps_to_server_error(self, adapter):
        with patch.object(anthropic.Anthropic, 'messages') as mock_messages:
            mock_request = MagicMock()
            mock_messages.create.side_effect = anthropic.APIError(
                message="server error",
                request=mock_request,
                body=None,
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.SERVER_ERROR
            assert exc_info.value.retryable


class TestAdapterClose:
    @pytest.mark.asyncio
    async def test_close_is_async(self, adapter):
        import inspect
        assert inspect.iscoroutinefunction(adapter.close)

    @pytest.mark.asyncio
    async def test_close_does_not_raise(self, adapter):
        await adapter.close()

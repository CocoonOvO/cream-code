from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import openai
from openai._exceptions import APIStatusError

from creamcode.adapters import OpenAIAdapter
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
    return OpenAIAdapter(
        api_key=mock_api_key,
        event_bus=event_bus,
        model="gpt-4o",
    )


class TestOpenAIAdapterBasic:
    def test_adapter_name(self, adapter):
        assert adapter.name == "openai"

    def test_adapter_supported_models(self, adapter):
        models = adapter.supported_models
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        assert "gpt-4-turbo" in models
        assert "gpt-3.5-turbo" in models

    def test_adapter_has_send_messages(self, adapter):
        import inspect
        assert inspect.iscoroutinefunction(adapter.send_messages)

    def test_adapter_has_stream_messages(self, adapter):
        import inspect
        assert inspect.isasyncgenfunction(adapter.stream_messages)


class TestMessageConversion:
    def test_convert_user_message(self):
        event_bus = EventBus()
        adapter = OpenAIAdapter(api_key="key", event_bus=event_bus)
        message = Message(role=MessageRole.USER, content="Hello")
        result = adapter._convert_message(message)
        assert result == {"role": "user", "content": "Hello"}

    def test_convert_assistant_message(self):
        event_bus = EventBus()
        adapter = OpenAIAdapter(api_key="key", event_bus=event_bus)
        message = Message(role=MessageRole.ASSISTANT, content="Hi there")
        result = adapter._convert_message(message)
        assert result == {"role": "assistant", "content": "Hi there"}

    def test_convert_system_message(self):
        event_bus = EventBus()
        adapter = OpenAIAdapter(api_key="key", event_bus=event_bus)
        message = Message(role=MessageRole.SYSTEM, content="You are helpful")
        result = adapter._convert_message(message)
        assert result == {"role": "system", "content": "You are helpful"}

    def test_convert_tool_message(self):
        event_bus = EventBus()
        adapter = OpenAIAdapter(api_key="key", event_bus=event_bus)
        message = Message(
            role=MessageRole.TOOL,
            content="tool result content",
            tool_call_id="tool_1",
        )
        result = adapter._convert_message(message)
        assert result["role"] == "tool"
        assert result["content"] == "tool result content"
        assert result["tool_call_id"] == "tool_1"

    def test_convert_tool_message_with_tool_calls(self):
        event_bus = EventBus()
        adapter = OpenAIAdapter(api_key="key", event_bus=event_bus)
        tool_calls = [
            ToolCall(id="tool_1", name="bash", arguments={"command": "ls"})
        ]
        message = Message(
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=tool_calls,
        )
        result = adapter._convert_message(message)
        assert result["role"] == "assistant"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "tool_1"
        assert result["tool_calls"][0]["function"]["name"] == "bash"


class TestToolConversion:
    def test_convert_tools_with_openai_function(self):
        tools = [
            Tool(
                name="get_weather",
                description="Get weather",
                parameters={},
                openai_function={
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
            )
        ]
        from creamcode.adapters import convert_tools_for_openai
        result = convert_tools_for_openai(tools)
        assert len(result) == 1
        assert result[0]["function"]["name"] == "get_weather"

    def test_convert_tools_without_openai_function(self):
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
        from creamcode.adapters import convert_tools_for_openai
        result = convert_tools_for_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "bash"
        assert result[0]["function"]["parameters"]["properties"]["command"]["type"] == "string"


class TestMockApiCalls:
    @pytest.fixture
    def mock_client(self):
        with patch.object(openai.OpenAI, 'chat') as mock_chat:
            yield mock_chat

    @pytest.mark.asyncio
    async def test_send_messages_success(self, adapter, mock_client):
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello!"
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.model = "gpt-4o"
        mock_client.completions.create.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = await adapter.send_messages(messages)

        assert result.content == "Hello!"
        assert result.model == "gpt-4o"
        assert result.stop_reason == "stop"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20

    @pytest.mark.asyncio
    async def test_send_messages_with_tool_calls(self, adapter, mock_client):
        mock_tool_call = MagicMock()
        mock_tool_call.id = "tool_1"
        mock_tool_call.function.name = "bash"
        mock_tool_call.function.arguments = {"command": "ls"}

        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_choice.finish_reason = "tool_calls"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.model = "gpt-4o"
        mock_client.completions.create.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Run ls")]
        result = await adapter.send_messages(messages)

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tool_1"
        assert result.tool_calls[0].name == "bash"
        assert result.tool_calls[0].arguments == {"command": "ls"}

    @pytest.mark.asyncio
    async def test_send_messages_with_tools(self, adapter, mock_client):
        mock_choice = MagicMock()
        mock_choice.message.content = "Done"
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 10
        mock_response.model = "gpt-4o"
        mock_client.completions.create.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Use tool")]
        tools = [Tool(
            name="bash",
            description="Run command",
            parameters={"type": "object", "properties": {"command": {"type": "string"}}}
        )]
        result = await adapter.send_messages(messages, tools=tools)

        assert result.content == "Done"
        mock_client.completions.create.assert_called_once()
        call_kwargs = mock_client.completions.create.call_args.kwargs
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) == 1


def make_api_error(error_class, message, status_code=400):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return error_class(message=message, response=mock_response, body=None)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_bad_request_error_maps_to_context_length(self, adapter):
        with patch.object(openai.OpenAI, 'chat') as mock_chat:
            mock_chat.completions.create.side_effect = make_api_error(
                openai.BadRequestError, "context length exceeded"
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.CONTEXT_LENGTH
            assert not exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_auth_error_maps_to_auth(self, adapter):
        with patch.object(openai.OpenAI, 'chat') as mock_chat:
            mock_chat.completions.create.side_effect = make_api_error(
                openai.AuthenticationError, "invalid api key"
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.AUTH
            assert not exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_retryable(self, adapter):
        with patch.object(openai.OpenAI, 'chat') as mock_chat:
            mock_chat.completions.create.side_effect = make_api_error(
                openai.RateLimitError, "rate limited"
            )

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.RATE_LIMIT
            assert exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_api_error_maps_to_server_error(self, adapter):
        with patch.object(openai.OpenAI, 'chat') as mock_chat:
            mock_request = MagicMock()
            mock_chat.completions.create.side_effect = openai.APIError(
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

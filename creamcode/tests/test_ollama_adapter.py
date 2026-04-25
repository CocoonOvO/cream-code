from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from creamcode.adapters import OllamaAdapter
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
    return "ollama"


@pytest.fixture
def adapter(event_bus, mock_api_key):
    return OllamaAdapter(
        api_key=mock_api_key,
        event_bus=event_bus,
        model="llama3.2",
    )


class TestOllamaAdapterBasic:
    def test_adapter_name(self, adapter):
        assert adapter.name == "ollama"

    def test_adapter_supported_models(self, adapter):
        models = adapter.supported_models
        assert "llama3.2" in models
        assert "qwen2.5" in models
        assert "codellama" in models
        assert "mistral" in models

    def test_adapter_has_send_messages(self, adapter):
        import inspect
        assert inspect.iscoroutinefunction(adapter.send_messages)

    def test_adapter_has_stream_messages(self, adapter):
        import inspect
        assert inspect.isasyncgenfunction(adapter.stream_messages)


class TestMessageConversion:
    def test_convert_user_message(self):
        event_bus = EventBus()
        adapter = OllamaAdapter(api_key="ollama", event_bus=event_bus)
        message = Message(role=MessageRole.USER, content="Hello")
        result = adapter._convert_message(message)
        assert result == {"role": "user", "content": "Hello"}

    def test_convert_assistant_message(self):
        event_bus = EventBus()
        adapter = OllamaAdapter(api_key="ollama", event_bus=event_bus)
        message = Message(role=MessageRole.ASSISTANT, content="Hi there")
        result = adapter._convert_message(message)
        assert result == {"role": "assistant", "content": "Hi there"}

    def test_convert_system_message(self):
        event_bus = EventBus()
        adapter = OllamaAdapter(api_key="ollama", event_bus=event_bus)
        message = Message(role=MessageRole.SYSTEM, content="You are helpful")
        result = adapter._convert_message(message)
        assert result == {"role": "system", "content": "You are helpful"}

    def test_convert_tool_message(self):
        event_bus = EventBus()
        adapter = OllamaAdapter(api_key="ollama", event_bus=event_bus)
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
        adapter = OllamaAdapter(api_key="ollama", event_bus=event_bus)
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


class TestMockApiCalls:
    @pytest.fixture
    def mock_http_client(self):
        with patch.object(httpx.AsyncClient, 'post') as mock_post:
            yield mock_post

    @pytest.mark.asyncio
    async def test_send_messages_success(self, adapter, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello!"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20
            },
            "model": "llama3.2"
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Hi")]
        result = await adapter.send_messages(messages)

        assert result.content == "Hello!"
        assert result.model == "llama3.2"
        assert result.stop_reason == "stop"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20

    @pytest.mark.asyncio
    async def test_send_messages_with_tool_calls(self, adapter, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "tool_1",
                        "function": {
                            "name": "bash",
                            "arguments": {"command": "ls"}
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5
            },
            "model": "llama3.2"
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Run ls")]
        result = await adapter.send_messages(messages)

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tool_1"
        assert result.tool_calls[0].name == "bash"
        assert result.tool_calls[0].arguments == {"command": "ls"}

    @pytest.mark.asyncio
    async def test_send_messages_with_tools(self, adapter, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Done"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 10
            },
            "model": "llama3.2"
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.return_value = mock_response

        messages = [Message(role=MessageRole.USER, content="Use tool")]
        tools = [Tool(
            name="bash",
            description="Run command",
            parameters={"type": "object", "properties": {"command": {"type": "string"}}}
        )]
        result = await adapter.send_messages(messages, tools=tools)

        assert result.content == "Done"
        mock_http_client.assert_called_once()
        call_kwargs = mock_http_client.call_args.kwargs
        assert call_kwargs["json"]["tools"] is not None
        assert len(call_kwargs["json"]["tools"]) == 1


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_timeout_error_is_retryable(self, adapter):
        with patch.object(httpx.AsyncClient, 'post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("timeout")

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.TIMEOUT
            assert exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_connect_error_is_not_retryable(self, adapter):
        with patch.object(httpx.AsyncClient, 'post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("connection refused")

            messages = [Message(role=MessageRole.USER, content="Hi")]
            with pytest.raises(AdapterError) as exc_info:
                await adapter.send_messages(messages)
            
            assert exc_info.value.code == AdapterErrorCode.UNKNOWN
            assert not exc_info.value.retryable

    @pytest.mark.asyncio
    async def test_http_status_error_is_retryable(self, adapter):
        with patch.object(httpx.AsyncClient, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.side_effect = httpx.HTTPStatusError(
                "server error",
                request=MagicMock(),
                response=mock_response
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
        with patch.object(httpx.AsyncClient, 'aclose') as mock_aclose:
            mock_aclose.return_value = AsyncMock()
            await adapter.close()

from __future__ import annotations

import asyncio
import inspect
import pytest

from creamcode.adapters import (
    ADAPTER_CREATED,
    ADAPTER_ERROR,
    ADAPTER_REQUEST,
    ADAPTER_RESPONSE,
    AdapterRegistry,
    BaseAdapter,
    RetryConfig,
    calculate_retry_delay,
    convert_tools_for_anthropic,
    convert_tools_for_openai,
    with_retry,
)
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
)


class MockAdapter(BaseAdapter):
    """Mock adapter for testing"""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def supported_models(self) -> list[str]:
        return ["mock-model-v1", "mock-model-v2"]

    async def send_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        return Response(content="mock response", model=model or self.model)

    async def stream_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        yield ResponseChunk(content="chunk1", is_final=False)
        yield ResponseChunk(content="chunk2", is_final=True)


class FailOnceAdapter(BaseAdapter):
    """Adapter that fails once then succeeds"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_count = 0

    @property
    def name(self) -> str:
        return "fail_once"

    async def send_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        self.fail_count += 1
        if self.fail_count == 1:
            raise AdapterError(
                code=AdapterErrorCode.RATE_LIMIT,
                message="Rate limited",
                retryable=True,
            )
        return Response(content="success after retry")

    async def stream_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        yield ResponseChunk(content="final", is_final=True)


class TestAdapterRegistry:
    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def registry(self, event_bus):
        return AdapterRegistry(event_bus)

    def test_register_adapter(self, registry):
        registry.register(MockAdapter)
        adapters = registry.list_adapters()
        assert "MockAdapter" in adapters

    @pytest.mark.asyncio
    async def test_create_adapter(self, registry, event_bus):
        registry.register(MockAdapter)

        received_events = []

        async def handler(event):
            received_events.append(event)

        await event_bus.subscribe(ADAPTER_CREATED, handler)

        adapter = await registry.create_adapter(
            name="MockAdapter",
            api_key="test-key",
            model="mock-model-v1",
        )

        assert adapter is not None
        assert adapter.api_key == "test-key"
        assert adapter.model == "mock-model-v1"
        assert len(received_events) == 1
        assert received_events[0].name == ADAPTER_CREATED
        assert received_events[0].data["adapter_name"] == "MockAdapter"

    @pytest.mark.asyncio
    async def test_get_adapter(self, registry):
        registry.register(MockAdapter)
        adapter = await registry.create_adapter(
            name="MockAdapter",
            api_key="test-key",
        )
        retrieved = registry.get_adapter("MockAdapter")
        assert retrieved is adapter

    @pytest.mark.asyncio
    async def test_get_adapter_not_found(self, registry):
        result = registry.get_adapter("NonExistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_adapters(self, registry):
        registry.register(MockAdapter)
        assert "MockAdapter" in registry.list_adapters()

    @pytest.mark.asyncio
    async def test_create_adapter_not_found(self, registry):
        with pytest.raises(ValueError) as exc_info:
            await registry.create_adapter(name="NonExistent", api_key="key")
        assert "NonExistent" in str(exc_info.value)


class TestRetryMechanism:
    def test_calculate_retry_delay(self):
        config = RetryConfig(base_delay=1.0, max_delay=60.0)
        delay1 = calculate_retry_delay(0, config)
        delay2 = calculate_retry_delay(1, config)
        delay3 = calculate_retry_delay(2, config)

        assert delay1 > 1.0
        assert delay2 > delay1
        assert delay3 > delay2

    def test_calculate_retry_delay_respects_max(self):
        config = RetryConfig(base_delay=10.0, max_delay=15.0)
        delay = calculate_retry_delay(10, config)
        assert delay <= 16.0

    @pytest.mark.asyncio
    async def test_with_retry_success_first_try(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(succeed, RetryConfig(max_attempts=3))
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_with_retry_retries_on_retryable_error(self):
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AdapterError(
                    code=AdapterErrorCode.RATE_LIMIT,
                    message="rate limited",
                    retryable=True,
                )
            return "success"

        result = await with_retry(fail_then_succeed, RetryConfig(max_attempts=3))
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_raises_non_retryable_error(self):
        async def fail():
            raise AdapterError(
                code=AdapterErrorCode.AUTH,
                message="auth failed",
                retryable=False,
            )

        with pytest.raises(AdapterError) as exc_info:
            await with_retry(fail, RetryConfig(max_attempts=3))
        assert exc_info.value.code == AdapterErrorCode.AUTH

    @pytest.mark.asyncio
    async def test_with_retry_respects_max_attempts(self):
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise AdapterError(
                code=AdapterErrorCode.RATE_LIMIT,
                message="rate limited",
                retryable=True,
            )

        with pytest.raises(AdapterError):
            await with_retry(always_fail, RetryConfig(max_attempts=3))
        assert call_count == 3


class TestToolConversion:
    def test_convert_tools_for_anthropic_with_preset_schema(self):
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
        result = convert_tools_for_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["input_schema"]["properties"]["location"]["type"] == "string"

    def test_convert_tools_for_anthropic_without_schema(self):
        tools = [
            Tool(
                name="search",
                description="Search the web",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            )
        ]
        result = convert_tools_for_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "search"
        assert result[0]["input_schema"]["properties"]["query"]["type"] == "string"

    def test_convert_tools_for_openai_with_preset_function(self):
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
        result = convert_tools_for_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "get_weather"

    def test_convert_tools_for_openai_without_function(self):
        tools = [
            Tool(
                name="search",
                description="Search the web",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            )
        ]
        result = convert_tools_for_openai(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "search"
        assert result[0]["function"]["parameters"]["properties"]["query"]["type"] == "string"


class TestAdapterEvents:
    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_adapter_created_event(self, event_bus):
        registry = AdapterRegistry(event_bus)
        registry.register(MockAdapter)

        received_events = []

        async def handler(event):
            received_events.append(event)

        await event_bus.subscribe(ADAPTER_CREATED, handler)

        await registry.create_adapter(name="MockAdapter", api_key="key")

        assert len(received_events) == 1
        assert received_events[0].name == ADAPTER_CREATED
        assert received_events[0].source == "registry"

    @pytest.mark.asyncio
    async def test_adapter_error_event(self, event_bus):
        received_events = []

        async def handler(event):
            received_events.append(event)

        await event_bus.subscribe(ADAPTER_ERROR, handler)

        class ErrorPublishingAdapter(BaseAdapter):
            @property
            def name(self) -> str:
                return "error_publisher"

            async def send_messages(self, messages, tools=None, model=None):
                raise AdapterError(
                    code=AdapterErrorCode.SERVER_ERROR,
                    message="Server error",
                    retryable=True,
                )

            async def stream_messages(self, messages, tools=None, model=None):
                yield ResponseChunk(content="")

            async def _publish_event(self, event_name: str, data: dict) -> None:
                from creamcode.types import Event
                event = Event(name=event_name, source=self.name, data=data)
                await self.event_bus.publish(event)

        adapter = ErrorPublishingAdapter(api_key="key", event_bus=event_bus)
        try:
            await adapter._handle_request([Message(role=MessageRole.USER, content="test")])
        except AdapterError:
            pass

        assert len(received_events) >= 1
        assert received_events[0].name == ADAPTER_ERROR


class TestBaseAdapterInterface:
    def test_adapter_has_name_property(self):
        assert hasattr(MockAdapter, "name")

    def test_adapter_has_supported_models_property(self):
        adapter = MockAdapter(api_key="key", event_bus=EventBus())
        assert isinstance(adapter.supported_models, list)

    def test_adapter_send_messages_is_async(self):
        assert asyncio.iscoroutinefunction(MockAdapter.send_messages)

    def test_adapter_stream_messages_is_async(self):
        # stream_messages is an async generator, not a regular coroutine
        assert inspect.isasyncgenfunction(MockAdapter.stream_messages)

    def test_adapter_close_is_async(self):
        adapter = MockAdapter(api_key="key", event_bus=EventBus())
        assert asyncio.iscoroutinefunction(adapter.close)


class TestRetryConfig:
    def test_default_values(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert "rate_limit" in config.retryable_codes
        assert "timeout" in config.retryable_codes
        assert "server_error" in config.retryable_codes

    def test_custom_values(self):
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0


class TestEventConstants:
    def test_adapter_events_defined(self):
        assert ADAPTER_CREATED == "adapter.created"
        assert ADAPTER_ERROR == "adapter.error"
        assert ADAPTER_REQUEST == "adapter.request"
        assert ADAPTER_RESPONSE == "adapter.response"

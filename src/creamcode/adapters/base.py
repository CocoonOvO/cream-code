from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from ..types import (
    AdapterError,
    Message,
    Response,
    ResponseChunk,
    RetryConfig,
    Tool,
)
from .events import ADAPTER_CREATED, ADAPTER_ERROR, ADAPTER_REQUEST, ADAPTER_RESPONSE
from .retry import with_retry


class BaseAdapter(ABC):
    """
    适配器基类
    所有模型适配器必须继承此类
    """

    def __init__(
        self,
        api_key: str,
        event_bus: Any,
        model: str | None = None,
        retry_config: RetryConfig | None = None,
    ):
        self.api_key = api_key
        self.event_bus = event_bus
        self.model = model
        self.retry_config = retry_config or RetryConfig()
        self._logger = None

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass

    @property
    def supported_models(self) -> list[str]:
        """支持的模型列表"""
        return []

    @abstractmethod
    async def send_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        """
        发送消息并获取响应
        """
        pass

    @abstractmethod
    async def stream_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        """
        流式响应
        """
        pass

    async def close(self):
        """关闭适配器，释放资源"""
        pass

    async def _publish_event(self, event_name: str, data: dict) -> None:
        """发布事件到事件总线"""
        from ..types import Event

        event = Event(name=event_name, source=self.name, data=data)
        await self.event_bus.publish(event)

    async def _handle_request(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        """处理请求的包装方法，发布事件"""
        await self._publish_event(ADAPTER_REQUEST, {
            "messages": messages,
            "tools": tools,
            "model": model or self.model,
        })

        try:
            response = await with_retry(
                lambda: self.send_messages(messages, tools, model),
                config=self.retry_config,
            )
            await self._publish_event(ADAPTER_RESPONSE, {
                "response": response,
            })
            return response
        except Exception as e:
            await self._publish_event(ADAPTER_ERROR, {
                "error": str(e),
                "type": type(e).__name__,
            })
            raise


def convert_tools_for_anthropic(tools: list[Tool]) -> list[dict]:
    """将统一 Tool 转换为 Claude 格式"""
    result = []
    for tool in tools:
        if tool.anthropic_schema:
            result.append(tool.anthropic_schema)
        else:
            result.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            })
    return result


def convert_tools_for_openai(tools: list[Tool]) -> list[dict]:
    """将统一 Tool 转换为 OpenAI 格式"""
    result = []
    for tool in tools:
        if tool.openai_function:
            result.append(tool.openai_function)
        else:
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
    return result

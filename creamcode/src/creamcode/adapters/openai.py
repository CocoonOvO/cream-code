import openai
from typing import AsyncIterator
import logging

from ..types import (
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
from .base import BaseAdapter, convert_tools_for_openai
from ..core.event_bus import EventBus


class OpenAIAdapter(BaseAdapter):
    """
    OpenAI GPT 适配器
    """

    def __init__(
        self,
        api_key: str,
        event_bus: EventBus,
        model: str = "gpt-4o",
        **kwargs,
    ):
        super().__init__(api_key=api_key, event_bus=event_bus, model=model, **kwargs)
        self._client = openai.OpenAI(api_key=api_key)
        self._logger = logging.getLogger("creamcode.adapter.openai")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> list[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

    def _convert_message(self, message: Message) -> dict:
        """将统一 Message 转换为 OpenAI 格式"""
        if message.role == MessageRole.SYSTEM:
            return {"role": "system", "content": message.content}
        elif message.role == MessageRole.TOOL:
            result = {"role": "tool", "content": message.content}
            if message.tool_call_id:
                result["tool_call_id"] = message.tool_call_id
            return result
        else:
            result = {"role": message.role.value, "content": message.content}
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments if isinstance(tc.arguments, str) else str(tc.arguments),
                        },
                    }
                    for tc in message.tool_calls
                ]
            return result

    async def send_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        """发送消息到 OpenAI API"""
        openai_messages = [self._convert_message(m) for m in messages]
        openai_tools = convert_tools_for_openai(tools) if tools else None

        try:
            response = self._client.chat.completions.create(
                model=model or self.model,
                messages=openai_messages,
                tools=openai_tools,
                tool_choice="auto" if tools else None,
            )

            content = ""
            tool_calls = None

            choice = response.choices[0]
            if choice.message.content:
                content = choice.message.content

            if choice.message.tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments if isinstance(tc.function.arguments, dict) else {},
                    )
                    for tc in choice.message.tool_calls
                ]

            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

            return Response(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model=response.model,
                stop_reason=choice.finish_reason,
            )

        except openai.BadRequestError as e:
            raise AdapterError(
                code=AdapterErrorCode.CONTEXT_LENGTH,
                message=str(e),
                retryable=False,
            )
        except openai.AuthenticationError as e:
            raise AdapterError(
                code=AdapterErrorCode.AUTH,
                message=str(e),
                retryable=False,
            )
        except openai.RateLimitError as e:
            raise AdapterError(
                code=AdapterErrorCode.RATE_LIMIT,
                message=str(e),
                retryable=True,
            )
        except openai.APIError as e:
            raise AdapterError(
                code=AdapterErrorCode.SERVER_ERROR,
                message=str(e),
                retryable=True,
            )

    async def stream_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        """流式响应"""
        openai_messages = [self._convert_message(m) for m in messages]
        openai_tools = convert_tools_for_openai(tools) if tools else None

        try:
            stream = self._client.chat.completions.create(
                model=model or self.model,
                messages=openai_messages,
                tools=openai_tools,
                stream=True,
            )

            current_tool_call = None
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield ResponseChunk(
                        content=delta.content,
                        is_final=False,
                    )
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if current_tool_call is None:
                            current_tool_call = ToolCall(
                                id=tc_delta.id or "",
                                name=tc_delta.function.name or "",
                                arguments={},
                            )
                        if tc_delta.function.arguments:
                            if isinstance(current_tool_call.arguments, str):
                                current_tool_call.arguments += tc_delta.function.arguments
                            else:
                                current_tool_call.arguments = tc_delta.function.arguments or {}
                if chunk.choices[0].finish_reason:
                    if current_tool_call:
                        yield ResponseChunk(
                            content="",
                            tool_call=current_tool_call,
                            is_final=True,
                        )
                    break

        except openai.BadRequestError as e:
            raise AdapterError(
                code=AdapterErrorCode.CONTEXT_LENGTH,
                message=str(e),
                retryable=False,
            )
        except openai.AuthenticationError as e:
            raise AdapterError(
                code=AdapterErrorCode.AUTH,
                message=str(e),
                retryable=False,
            )
        except openai.RateLimitError as e:
            raise AdapterError(
                code=AdapterErrorCode.RATE_LIMIT,
                message=str(e),
                retryable=True,
            )
        except openai.APIError as e:
            raise AdapterError(
                code=AdapterErrorCode.SERVER_ERROR,
                message=str(e),
                retryable=True,
            )

    async def close(self):
        """关闭适配器，释放资源"""
        pass

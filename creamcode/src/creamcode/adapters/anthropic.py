import anthropic
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
    ToolResult,
    TokenUsage,
)
from .base import BaseAdapter, convert_tools_for_anthropic
from ..core.event_bus import EventBus


class AnthropicAdapter(BaseAdapter):
    """
    Anthropic Claude 适配器
    """

    def __init__(
        self,
        api_key: str,
        event_bus: EventBus,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        **kwargs,
    ):
        super().__init__(api_key=api_key, event_bus=event_bus, model=model, **kwargs)
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key)
        self._logger = logging.getLogger("creamcode.adapter.anthropic")

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> list[str]:
        return [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-haiku-4-20250507",
        ]

    def _convert_message(self, message: Message) -> dict:
        """将统一 Message 转换为 Claude 格式"""
        if message.role == MessageRole.SYSTEM:
            return {"role": "user", "content": f"[System] {message.content}"}
        elif message.role == MessageRole.TOOL:
            tool_content = message.content
            if message.tool_calls:
                tool_content = []
                for tc in message.tool_calls:
                    tool_content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
            return {"role": "user", "content": tool_content}
        else:
            return {"role": message.role.value, "content": message.content}

    async def send_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        """发送消息到 Claude API"""
        claude_messages = [self._convert_message(m) for m in messages]
        claude_tools = convert_tools_for_anthropic(tools) if tools else None

        try:
            response = self._client.messages.create(
                model=model or self.model,
                max_tokens=self.max_tokens,
                messages=claude_messages,
                tools=claude_tools,
            )

            content = ""
            tool_calls = None

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls = tool_calls or []
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    ))

            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return Response(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model=response.model,
                stop_reason=response.stop_reason,
            )

        except anthropic.BadRequestError as e:
            raise AdapterError(
                code=AdapterErrorCode.CONTEXT_LENGTH,
                message=str(e),
                retryable=False,
            )
        except anthropic.AuthenticationError as e:
            raise AdapterError(
                code=AdapterErrorCode.AUTH,
                message=str(e),
                retryable=False,
            )
        except anthropic.RateLimitError as e:
            raise AdapterError(
                code=AdapterErrorCode.RATE_LIMIT,
                message=str(e),
                retryable=True,
            )
        except anthropic.APIError as e:
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
        claude_messages = [self._convert_message(m) for m in messages]
        claude_tools = convert_tools_for_anthropic(tools) if tools else None

        try:
            with self._client.messages.stream(
                model=model or self.model,
                max_tokens=self.max_tokens,
                messages=claude_messages,
                tools=claude_tools,
            ) as stream:
                current_tool_call = None
                for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield ResponseChunk(
                                content=event.delta.text,
                                is_final=False,
                            )
                        elif event.delta.type == "input_json_delta":
                            if current_tool_call is None:
                                current_tool_call = ToolCall(
                                    id="",
                                    name="",
                                    arguments={},
                                )
                            if isinstance(current_tool_call.arguments, str):
                                current_tool_call.arguments += event.delta.partial_json
                            else:
                                current_tool_call.arguments = event.delta.partial_json
                    elif event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_tool_call = ToolCall(
                                id=event.content_block.id,
                                name=event.content_block.name,
                                arguments={},
                            )
                    elif event.type == "message_delta":
                        if current_tool_call:
                            yield ResponseChunk(
                                content="",
                                tool_call=current_tool_call,
                                is_final=True,
                            )
                            current_tool_call = None

        except anthropic.BadRequestError as e:
            raise AdapterError(
                code=AdapterErrorCode.CONTEXT_LENGTH,
                message=str(e),
                retryable=False,
            )
        except anthropic.AuthenticationError as e:
            raise AdapterError(
                code=AdapterErrorCode.AUTH,
                message=str(e),
                retryable=False,
            )
        except anthropic.RateLimitError as e:
            raise AdapterError(
                code=AdapterErrorCode.RATE_LIMIT,
                message=str(e),
                retryable=True,
            )
        except anthropic.APIError as e:
            raise AdapterError(
                code=AdapterErrorCode.SERVER_ERROR,
                message=str(e),
                retryable=True,
            )

    async def close(self):
        """关闭适配器，释放资源"""
        pass

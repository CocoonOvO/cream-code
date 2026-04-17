import httpx
from typing import AsyncIterator
import logging
import json

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


class MiniMaxAdapter(BaseAdapter):
    """
    MiniMax 适配器
    """

    def __init__(
        self,
        api_key: str,
        event_bus: EventBus = None,
        model: str = "MiniMax-Text-01",
        base_url: str = "https://api.minimax.chat/v1",
        **kwargs,
    ):
        super().__init__(api_key=api_key, event_bus=event_bus, model=model, **kwargs)
        self.base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
        self._logger = logging.getLogger("creamcode.adapter.minimax")

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def supported_models(self) -> list[str]:
        return ["MiniMax-Text-01", "abab6.5s-chat", "abab6.5g-chat"]

    def _convert_message(self, message: Message) -> dict:
        """将统一 Message 转换为 MiniMax 格式"""
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
                            "arguments": tc.arguments if isinstance(tc.arguments, str) else json.dumps(tc.arguments),
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
        """发送消息到 MiniMax API"""
        minimax_messages = [self._convert_message(m) for m in messages]
        minimax_tools = convert_tools_for_openai(tools) if tools else None

        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": model or self.model,
                    "messages": minimax_messages,
                    "tools": minimax_tools,
                    "tool_choice": "auto" if tools else None,
                },
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message = choice["message"]

            content = message.get("content") or ""

            tool_calls = None
            if message.get("tool_calls"):
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        name=tc["function"]["name"],
                        arguments=json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"],
                    )
                    for tc in message["tool_calls"]
                ]

            usage = None
            if "usage" in data:
                usage = TokenUsage(
                    input_tokens=data["usage"].get("prompt_tokens", 0),
                    output_tokens=data["usage"].get("completion_tokens", 0),
                )

            return Response(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model=data.get("model"),
                stop_reason=choice.get("finish_reason"),
            )

        except httpx.TimeoutException as e:
            raise AdapterError(
                code=AdapterErrorCode.TIMEOUT,
                message=str(e),
                retryable=True,
            )
        except httpx.ConnectError as e:
            raise AdapterError(
                code=AdapterErrorCode.UNKNOWN,
                message=str(e),
                retryable=False,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AdapterError(
                    code=AdapterErrorCode.AUTH,
                    message=str(e),
                    retryable=False,
                )
            elif e.response.status_code == 429:
                raise AdapterError(
                    code=AdapterErrorCode.RATE_LIMIT,
                    message=str(e),
                    retryable=True,
                )
            elif e.response.status_code == 400 and "context" in str(e).lower():
                raise AdapterError(
                    code=AdapterErrorCode.CONTEXT_LENGTH,
                    message=str(e),
                    retryable=False,
                )
            else:
                raise AdapterError(
                    code=AdapterErrorCode.SERVER_ERROR,
                    message=str(e),
                    retryable=True,
                )
        except Exception as e:
            raise AdapterError(
                code=AdapterErrorCode.UNKNOWN,
                message=str(e),
                retryable=False,
            )

    async def stream_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        """流式响应"""
        minimax_messages = [self._convert_message(m) for m in messages]
        minimax_tools = convert_tools_for_openai(tools) if tools else None

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": model or self.model,
                    "messages": minimax_messages,
                    "tools": minimax_tools,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                current_tool_call = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        if current_tool_call:
                            yield ResponseChunk(
                                content="",
                                tool_call=current_tool_call,
                                is_final=True,
                            )
                        break

                    data = json.loads(data_str)
                    choice = data.get("choices", [{}])[0]
                    delta = choice.get("delta", {})

                    if delta.get("content"):
                        yield ResponseChunk(
                            content=delta["content"],
                            is_final=False,
                        )

                    if delta.get("tool_calls"):
                        for tc_delta in delta["tool_calls"]:
                            if current_tool_call is None:
                                current_tool_call = ToolCall(
                                    id=tc_delta.get("id") or "",
                                    name=tc_delta.get("function", {}).get("name") or "",
                                    arguments={},
                                )
                            if tc_delta.get("function", {}).get("arguments"):
                                if isinstance(current_tool_call.arguments, str):
                                    current_tool_call.arguments += tc_delta["function"]["arguments"]
                                else:
                                    current_tool_call.arguments = json.loads(tc_delta["function"]["arguments"])

                    if choice.get("finish_reason"):
                        if current_tool_call:
                            yield ResponseChunk(
                                content="",
                                tool_call=current_tool_call,
                                is_final=True,
                            )
                        break

        except httpx.TimeoutException as e:
            raise AdapterError(
                code=AdapterErrorCode.TIMEOUT,
                message=str(e),
                retryable=True,
            )
        except httpx.ConnectError as e:
            raise AdapterError(
                code=AdapterErrorCode.UNKNOWN,
                message=str(e),
                retryable=False,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AdapterError(
                    code=AdapterErrorCode.AUTH,
                    message=str(e),
                    retryable=False,
                )
            elif e.response.status_code == 429:
                raise AdapterError(
                    code=AdapterErrorCode.RATE_LIMIT,
                    message=str(e),
                    retryable=True,
                )
            else:
                raise AdapterError(
                    code=AdapterErrorCode.SERVER_ERROR,
                    message=str(e),
                    retryable=True,
                )
        except Exception as e:
            raise AdapterError(
                code=AdapterErrorCode.UNKNOWN,
                message=str(e),
                retryable=False,
            )

    async def close(self):
        """关闭适配器，释放资源"""
        await self._client.aclose()

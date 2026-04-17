import httpx
import json
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


class OllamaAdapter(BaseAdapter):
    """
    Ollama 本地模型适配器
    """

    def __init__(
        self,
        api_key: str = "ollama",
        event_bus: EventBus = None,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        **kwargs,
    ):
        super().__init__(api_key=api_key, event_bus=event_bus, model=model, **kwargs)
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)
        self._logger = logging.getLogger("creamcode.adapter.ollama")

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def supported_models(self) -> list[str]:
        return ["llama3.2", "qwen2.5", "codellama", "mistral"]

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
        """发送消息到 Ollama API"""
        ollama_messages = [self._convert_message(m) for m in messages]
        ollama_tools = convert_tools_for_openai(tools) if tools else None

        try:
            response = await self._client.post(
                "/v1/chat/completions",
                json={
                    "model": model or self.model,
                    "messages": ollama_messages,
                    "tools": ollama_tools,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = ""
            tool_calls = None

            choice = data["choices"][0]
            if choice["message"].get("content"):
                content = choice["message"]["content"]

            if choice["message"].get("tool_calls"):
                tool_calls = [
                    ToolCall(
                        id=tc["id"],
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"] if isinstance(tc["function"]["arguments"], dict) else {},
                    )
                    for tc in choice["message"]["tool_calls"]
                ]

            usage = data.get("usage", {})
            token_usage = TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )

            return Response(
                content=content,
                tool_calls=tool_calls,
                usage=token_usage,
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
        ollama_messages = [self._convert_message(m) for m in messages]
        ollama_tools = convert_tools_for_openai(tools) if tools else None

        try:
            async with self._client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": model or self.model,
                    "messages": ollama_messages,
                    "tools": ollama_tools,
                    "stream": True,
                },
            ) as stream:
                stream.raise_for_status()
                current_tool_call = None

                async for line in stream.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        if current_tool_call:
                            yield ResponseChunk(
                                content="",
                                tool_call=current_tool_call,
                                is_final=True,
                            )
                        break

                    data = json.loads(data_str)

                    if data.get("choices"):
                        delta = data["choices"][0].get("delta", {})
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
                                    args = tc_delta["function"]["arguments"]
                                    if isinstance(current_tool_call.arguments, str):
                                        current_tool_call.arguments += args
                                    else:
                                        current_tool_call.arguments = args or {}

                        finish_reason = data["choices"][0].get("finish_reason")
                        if finish_reason:
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
            raise AdapterError(
                code=AdapterErrorCode.SERVER_ERROR,
                message=str(e),
                retryable=True,
            )

    async def close(self):
        """关闭适配器，释放资源"""
        await self._client.aclose()

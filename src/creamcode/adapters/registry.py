from typing import Any

from ..types import Event, RetryConfig
from .base import BaseAdapter
from .events import ADAPTER_CREATED, ADAPTER_ERROR


class AdapterRegistry:
    """
    适配器注册表
    管理所有可用适配器
    """

    def __init__(self, event_bus: Any):
        self._adapters: dict[str, type[BaseAdapter]] = {}
        self._instances: dict[str, BaseAdapter] = {}
        self._event_bus = event_bus

    def register(self, adapter_class: type[BaseAdapter]) -> None:
        """注册适配器类"""
        self._adapters[adapter_class.__name__] = adapter_class

    async def create_adapter(
        self,
        name: str,
        api_key: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> BaseAdapter:
        """创建适配器实例"""
        if name not in self._adapters:
            raise ValueError(f"Adapter '{name}' not found. Available: {list(self._adapters.keys())}")

        adapter_class = self._adapters[name]
        adapter = adapter_class(
            api_key=api_key,
            event_bus=self._event_bus,
            model=model,
            **kwargs,
        )

        self._instances[name] = adapter

        await self._event_bus.publish(Event(
            name=ADAPTER_CREATED,
            source="registry",
            data={"adapter_name": name, "model": model},
        ))

        return adapter

    def get_adapter(self, name: str) -> BaseAdapter | None:
        """获取已创建的适配器实例"""
        return self._instances.get(name)

    def list_adapters(self) -> list[str]:
        """列出所有已注册的适配器"""
        return list(self._adapters.keys())

    def list_instances(self) -> list[str]:
        """列出所有已创建的适配器实例"""
        return list(self._instances.keys())

    async def close_all(self) -> None:
        """关闭所有适配器实例"""
        for adapter in self._instances.values():
            await adapter.close()
        self._instances.clear()

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppConfig:
    """应用配置"""

    debug: bool = False
    verbose: bool = False

    default_adapter: str = "anthropic"
    default_model: str | None = None

    max_tokens: int = 100000
    reserved_tokens: int = 4096

    max_summaries: int = 10

    storage_dir: str = "~/.cache/creamcode"
    plugin_dirs: list[str] = field(default_factory=list)

    budget_strategy: str = "warn"
    monthly_budget: float | None = None

    adapter_configs: dict[str, dict] = field(default_factory=dict)

    mcp_servers: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """从字典创建配置"""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {f.name: getattr(self, f.name) for f in self.__dataclass_fields__.values()}
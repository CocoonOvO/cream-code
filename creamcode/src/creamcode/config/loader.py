from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import AppConfig


class ConfigLoader:
    """配置加载器 - 支持多层合并"""

    DEFAULT_CONFIG_LOCATIONS = [
        Path("~/.config/creamcode/config.json").expanduser(),
        Path(".creamcode.json"),
    ]

    def __init__(self, config_paths: list[Path] | None = None):
        self.config_paths = config_paths or self.DEFAULT_CONFIG_LOCATIONS

    def load(self, cli_overrides: dict[str, Any] | None = None) -> AppConfig:
        """
        加载配置，合并多层配置
        优先级：cli_overrides > 项目配置 > 全局配置
        """
        base_config = self._load_base_config()
        merged = self._merge_configs(base_config, cli_overrides or {})
        return AppConfig.from_dict(merged)

    def _load_base_config(self) -> dict[str, Any]:
        """从文件加载基础配置"""
        merged: dict[str, Any] = {}
        for path in self.config_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    merged = self._merge_configs(merged, data)
                except (json.JSONDecodeError, IOError):
                    continue
        return merged

    def _merge_configs(self, base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        """深度合并配置"""
        result = base.copy()
        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def save(self, config: AppConfig, path: Path) -> None:
        """保存配置到文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2)
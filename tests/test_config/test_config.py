from __future__ import annotations

import pytest

from creamcode.config import AppConfig


class TestAppConfig:
    """AppConfig 测试"""

    def test_default_creation(self):
        """测试默认配置创建"""
        config = AppConfig()
        assert config.debug is False
        assert config.verbose is False
        assert config.default_adapter == "anthropic"
        assert config.default_model is None
        assert config.max_tokens == 100000
        assert config.reserved_tokens == 4096
        assert config.max_summaries == 10
        assert config.storage_dir == "~/.cache/creamcode"
        assert config.plugin_dirs == []
        assert config.budget_strategy == "warn"
        assert config.monthly_budget is None
        assert config.adapter_configs == {}
        assert config.mcp_servers == {}

    def test_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "debug": True,
            "default_adapter": "openai",
            "max_tokens": 50000,
            "unknown_field": "should_be_ignored",
        }
        config = AppConfig.from_dict(data)
        assert config.debug is True
        assert config.default_adapter == "openai"
        assert config.max_tokens == 50000
        assert not hasattr(config, "unknown_field")

    def test_to_dict(self):
        """测试转换为字典"""
        config = AppConfig(
            debug=True,
            default_adapter="openai",
            max_tokens=50000,
        )
        result = config.to_dict()
        assert result["debug"] is True
        assert result["default_adapter"] == "openai"
        assert result["max_tokens"] == 50000
        assert "storage_dir" in result

    def test_field_access(self):
        """测试字段访问"""
        config = AppConfig(storage_dir="/custom/path")
        assert config.storage_dir == "/custom/path"
        config.storage_dir = "/another/path"
        assert config.storage_dir == "/another/path"

    def test_nested_dict_fields(self):
        """测试嵌套字典字段"""
        config = AppConfig(
            adapter_configs={"anthropic": {"api_key": "test-key"}},
            mcp_servers={"server1": {"url": "http://localhost"}},
        )
        assert config.adapter_configs["anthropic"]["api_key"] == "test-key"
        assert config.mcp_servers["server1"]["url"] == "http://localhost"

    def test_list_field(self):
        """测试列表字段"""
        config = AppConfig(plugin_dirs=["/plugin1", "/plugin2"])
        assert config.plugin_dirs == ["/plugin1", "/plugin2"]
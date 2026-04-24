from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from creamcode.config import AppConfig, ConfigLoader


class TestConfigLoader:
    """ConfigLoader 测试"""

    def test_load_from_empty_files(self):
        """测试从不存在配置文件加载"""
        loader = ConfigLoader(config_paths=[Path("/nonexistent/config.json")])
        config = loader.load()
        assert isinstance(config, AppConfig)
        assert config.debug is False

    def test_load_from_single_file(self):
        """测试从单个配置文件加载"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({"debug": True, "max_tokens": 50000}, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(config_paths=[temp_path])
            config = loader.load()
            assert config.debug is True
            assert config.max_tokens == 50000
        finally:
            temp_path.unlink()

    def test_merge_priority_global_over_default(self):
        """测试全局配置优先级（低）"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({"debug": True, "storage_dir": "/global/path"}, f)
            global_path = Path(f.name)

        try:
            loader = ConfigLoader(config_paths=[global_path])
            config = loader.load()
            assert config.debug is True
            assert config.storage_dir == "/global/path"
        finally:
            global_path.unlink()

    def test_merge_priority_project_over_global(self):
        """测试项目配置优先级高于全局配置"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({"debug": True, "storage_dir": "/global"}, f)
            global_path = Path(f.name)

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({"debug": False, "default_adapter": "openai"}, f)
            project_path = Path(f.name)

        try:
            loader = ConfigLoader(config_paths=[global_path, project_path])
            config = loader.load()
            assert config.debug is False
            assert config.default_adapter == "openai"
            assert config.storage_dir == "/global"
        finally:
            global_path.unlink()
            project_path.unlink()

    def test_merge_priority_cli_over_all(self):
        """测试 CLI 参数优先级最高"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({"debug": True, "max_tokens": 50000}, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(config_paths=[temp_path])
            config = loader.load(cli_overrides={"debug": False, "max_tokens": 100000})
            assert config.debug is False
            assert config.max_tokens == 100000
        finally:
            temp_path.unlink()

    def test_deep_merge_nested_dicts(self):
        """测试深度合并嵌套字典"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({
                "adapter_configs": {
                    "anthropic": {"api_key": "key1", "timeout": 30}
                }
            }, f)
            global_path = Path(f.name)

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({
                "adapter_configs": {
                    "anthropic": {"timeout": 60},
                    "openai": {"api_key": "key2"}
                }
            }, f)
            project_path = Path(f.name)

        try:
            loader = ConfigLoader(config_paths=[global_path, project_path])
            config = loader.load()
            assert config.adapter_configs["anthropic"]["api_key"] == "key1"
            assert config.adapter_configs["anthropic"]["timeout"] == 60
            assert config.adapter_configs["openai"]["api_key"] == "key2"
        finally:
            global_path.unlink()
            project_path.unlink()

    def test_save_config(self):
        """测试保存配置到文件"""
        config = AppConfig(debug=True, max_tokens=50000)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader()
            loader.save(config, temp_path)
            assert temp_path.exists()
            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data["debug"] is True
            assert saved_data["max_tokens"] == 50000
        finally:
            temp_path.unlink()

    def test_save_creates_parent_dirs(self):
        """测试保存时创建父目录"""
        config = AppConfig()
        temp_dir = tempfile.mkdtemp()
        save_path = Path(temp_dir) / "subdir" / "config.json"

        try:
            loader = ConfigLoader()
            loader.save(config, save_path)
            assert save_path.exists()
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_load_invalid_json(self):
        """测试加载无效 JSON 文件"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write("not valid json {")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(config_paths=[temp_path])
            config = loader.load()
            assert isinstance(config, AppConfig)
        finally:
            temp_path.unlink()
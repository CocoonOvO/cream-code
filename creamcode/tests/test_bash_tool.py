from __future__ import annotations

import asyncio
import pytest

from creamcode.core.event_bus import EventBus
from creamcode.tools.registry import ToolRegistry
from creamcode.tools.decorator import set_global_registry, get_global_registry
from creamcode.tools.bash import bash


class TestBashToolBasic:
    def test_bash_function_is_callable(self):
        assert callable(bash)

    def test_bash_has_tool_metadata(self):
        assert hasattr(bash, '_is_tool')
        assert bash._is_tool is True
        assert bash._tool_name == "Bash"

    @pytest.mark.asyncio
    async def test_bash_executes_simple_command(self):
        result = await bash("echo hello")
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_bash_returns_output(self):
        result = await bash("echo world")
        assert "world" in result

    @pytest.mark.asyncio
    async def test_bash_with_args(self):
        result = await bash("python --version")
        assert "Python" in result or "python" in result.lower()


class TestBashToolRegistration:
    def test_bash_registered_in_registry(self):
        set_global_registry(None)
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)
        
        from creamcode.tools import bash as bash_module
        import importlib
        importlib.reload(bash_module)
        
        assert registry.has_tool("Bash")
        set_global_registry(None)

    @pytest.mark.asyncio
    async def test_bash_via_registry(self):
        set_global_registry(None)
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)
        
        from creamcode.tools import bash as bash_module
        import importlib
        importlib.reload(bash_module)
        
        result = await registry.call_tool("Bash", {"command": "echo test"}, "call_1")
        assert "test" in result.content
        set_global_registry(None)


class TestBashToolErrorHandling:
    @pytest.mark.asyncio
    async def test_bash_invalid_command(self):
        result = await bash("nonexistentcommand12345")
        assert "exit code" in result or "error" in result.lower() or "not recognized" in result.lower() or "failed" in result.lower()

    @pytest.mark.asyncio
    async def test_bash_timeout(self):
        import sys
        if sys.platform == "win32":
            result = await bash("powershell -Command \"Start-Sleep -Seconds 100\"", timeout=1)
        else:
            result = await bash("sleep 100", timeout=1)
        assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_bash_nonexistent_command_error(self):
        result = await bash("commandthatdoesnotexist_abc123")
        assert "exit code" in result or "error" in result.lower() or "not recognized" in result.lower()


class TestBashToolMock:
    @pytest.mark.asyncio
    async def test_bash_mock_simulation(self):
        original_create_subprocess_shell = asyncio.create_subprocess_shell
        
        class MockProcess:
            returncode = 0
            async def communicate(self):
                return (b'mocked output', b'')
        
        async def mock_subprocess_shell(*args, **kwargs):
            return MockProcess()
        
        asyncio.create_subprocess_shell = mock_subprocess_shell
        
        try:
            result = await bash("echo mocked")
            assert "mocked" in result
        finally:
            asyncio.create_subprocess_shell = original_create_subprocess_shell

    @pytest.mark.asyncio
    async def test_bash_stderr_captured(self):
        result = await bash("python -c \"import sys; sys.stderr.write('error_msg')\" 2>&1")
        assert "error_msg" in result or "error" in result.lower()


class TestBashToolEdgeCases:
    @pytest.mark.asyncio
    async def test_bash_empty_command(self):
        result = await bash("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_bash_command_with_special_chars(self):
        result = await bash("echo $PATH")
        assert result is not None

    @pytest.mark.asyncio
    async def test_bash_cwd_parameter(self, tmp_path):
        result = await bash("echo test", cwd=str(tmp_path))
        assert "test" in result

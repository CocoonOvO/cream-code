from __future__ import annotations

import pytest

from creamcode.tools.decorator import set_global_registry, get_global_registry
from creamcode.tools.file import file_read, file_write, file_edit


class TestFileReadTool:
    def test_file_read_function_is_callable(self):
        assert callable(file_read)

    def test_file_read_has_tool_metadata(self):
        assert hasattr(file_read, '_is_tool')
        assert file_read._is_tool is True
        assert file_read._tool_name == "FileRead"

    @pytest.mark.asyncio
    async def test_file_read_existing_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding='utf-8')
        
        result = await file_read(str(test_file))
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    @pytest.mark.asyncio
    async def test_file_read_nonexistent_file(self):
        result = await file_read("nonexistent_file_12345.txt")
        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_file_read_with_limit(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding='utf-8')
        
        result = await file_read(str(test_file), limit=2)
        lines = result.strip().split('\n')
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_file_read_with_offset(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding='utf-8')
        
        result = await file_read(str(test_file), offset=1)
        assert "Line 2" in result
        assert "Line 1" not in result

    @pytest.mark.asyncio
    async def test_file_read_with_offset_and_limit(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5", encoding='utf-8')
        
        result = await file_read(str(test_file), limit=2, offset=1)
        lines = result.strip().split('\n')
        assert len(lines) == 2
        assert "Line 2" in result
        assert "Line 3" in result


class TestFileWriteTool:
    def test_file_write_function_is_callable(self):
        assert callable(file_write)

    def test_file_write_has_tool_metadata(self):
        assert hasattr(file_write, '_is_tool')
        assert file_write._is_tool is True
        assert file_write._tool_name == "FileWrite"

    @pytest.mark.asyncio
    async def test_file_write_new_file(self, tmp_path):
        test_file = tmp_path / "new_file.txt"
        
        result = await file_write(str(test_file), "Hello World")
        assert "Written to" in result
        assert test_file.read_text(encoding='utf-8') == "Hello World"

    @pytest.mark.asyncio
    async def test_file_write_overwrite(self, tmp_path):
        test_file = tmp_path / "overwrite.txt"
        test_file.write_text("Original content", encoding='utf-8')
        
        result = await file_write(str(test_file), "New content")
        assert "Written to" in result
        assert test_file.read_text(encoding='utf-8') == "New content"

    @pytest.mark.asyncio
    async def test_file_write_append_mode(self, tmp_path):
        test_file = tmp_path / "append.txt"
        test_file.write_text("Line 1", encoding='utf-8')
        
        result = await file_write(str(test_file), "\nLine 2", append=True)
        assert "Appended to" in result
        assert test_file.read_text(encoding='utf-8') == "Line 1\nLine 2"

    @pytest.mark.asyncio
    async def test_file_write_nonexistent_directory(self, tmp_path):
        nonexistent_dir = tmp_path / "nonexistent_dir"
        test_file = nonexistent_dir / "file.txt"
        
        result = await file_write(str(test_file), "content")
        assert "Error" in result
        assert "directory" in result.lower() or "exist" in result.lower()


class TestFileEditTool:
    def test_file_edit_function_is_callable(self):
        assert callable(file_edit)

    def test_file_edit_has_tool_metadata(self):
        assert hasattr(file_edit, '_is_tool')
        assert file_edit._is_tool is True
        assert file_edit._tool_name == "FileEdit"

    @pytest.mark.asyncio
    async def test_file_edit_replace_content(self, tmp_path):
        test_file = tmp_path / "edit_test.txt"
        test_file.write_text("Hello World", encoding='utf-8')
        
        result = await file_edit(str(test_file), "World", "Universe")
        assert "Edited" in result
        assert test_file.read_text(encoding='utf-8') == "Hello Universe"

    @pytest.mark.asyncio
    async def test_file_edit_replace_nonexistent_content(self, tmp_path):
        test_file = tmp_path / "edit_test.txt"
        test_file.write_text("Hello World", encoding='utf-8')
        
        result = await file_edit(str(test_file), "NonExistent", "Something")
        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_file_edit_nonexistent_file(self):
        result = await file_edit("nonexistent_file_12345.txt", "old", "new")
        assert "Error" in result
        assert "not found" in result.lower()


class TestFileToolPathTraversal:
    @pytest.mark.asyncio
    async def test_file_read_path_traversal(self):
        result = await file_read("../secret.txt")
        assert "Error" in result
        assert "traversal" in result.lower()

    @pytest.mark.asyncio
    async def test_file_write_path_traversal(self):
        result = await file_write("../secret.txt", "content")
        assert "Error" in result
        assert "traversal" in result.lower()

    @pytest.mark.asyncio
    async def test_file_edit_path_traversal(self):
        result = await file_edit("../secret.txt", "old", "new")
        assert "Error" in result
        assert "traversal" in result.lower()


class TestFileToolRegistration:
    def test_file_tools_registered_in_registry(self):
        set_global_registry(None)
        from creamcode.core.event_bus import EventBus
        from creamcode.tools.registry import ToolRegistry
        
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)
        
        from creamcode.tools import file as file_module
        import importlib
        importlib.reload(file_module)
        
        assert registry.has_tool("FileRead")
        assert registry.has_tool("FileWrite")
        assert registry.has_tool("FileEdit")
        set_global_registry(None)

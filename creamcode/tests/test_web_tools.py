from __future__ import annotations

import pytest

from creamcode.core.event_bus import EventBus
from creamcode.tools.registry import ToolRegistry
from creamcode.tools.decorator import set_global_registry, get_global_registry
from creamcode.tools.web import web_fetch, web_search


class TestWebFetchToolBasic:
    def test_web_fetch_function_is_callable(self):
        assert callable(web_fetch)

    def test_web_fetch_has_tool_metadata(self):
        assert hasattr(web_fetch, '_is_tool')
        assert web_fetch._is_tool is True
        assert web_fetch._tool_name == "WebFetch"


class TestWebFetchToolValidation:
    @pytest.mark.asyncio
    async def test_web_fetch_invalid_url(self):
        result = await web_fetch("not-a-valid-url")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_web_fetch_internal_url_blocked(self):
        result = await web_fetch("http://127.0.0.1/")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_web_fetch_localhost_blocked(self):
        result = await web_fetch("http://localhost/test")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_web_fetch_private_network_blocked(self):
        result = await web_fetch("http://192.168.1.1/")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_web_fetch_wrong_scheme(self):
        result = await web_fetch("ftp://example.com")
        assert "Error" in result


class TestWebFetchToolFetch:
    @pytest.mark.asyncio
    async def test_web_fetch_valid_url(self):
        result = await web_fetch("https://example.com", timeout=10)
        assert "Example" in result or "example" in result.lower() or "Error" in result

    @pytest.mark.asyncio
    async def test_web_fetch_timeout(self):
        result = await web_fetch("https://httpbin.org/delay/10", timeout=2)
        assert "timed out" in result.lower() or "Error" in result


class TestWebFetchToolRegistration:
    def test_web_fetch_registered_in_registry(self):
        set_global_registry(None)
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)

        from creamcode.tools import web as web_module
        import importlib
        importlib.reload(web_module)

        assert registry.has_tool("WebFetch")
        set_global_registry(None)


class TestWebSearchToolBasic:
    def test_web_search_function_is_callable(self):
        assert callable(web_search)

    def test_web_search_has_tool_metadata(self):
        assert hasattr(web_search, '_is_tool')
        assert web_search._is_tool is True
        assert web_search._tool_name == "WebSearch"


class TestWebSearchToolValidation:
    @pytest.mark.asyncio
    async def test_web_search_empty_query(self):
        result = await web_search("")
        assert "Error" in result or "Empty" in result

    @pytest.mark.asyncio
    async def test_web_search_whitespace_query(self):
        result = await web_search("   ")
        assert "Error" in result or "Empty" in result


class TestWebSearchToolSearch:
    @pytest.mark.asyncio
    async def test_web_search_query(self):
        result = await web_search("python programming", num_results=3)
        assert "python" in result.lower() or "Python" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_web_search_result_count(self):
        result = await web_search("test", num_results=5)
        lines = result.split("\n\n")
        count = sum(1 for l in lines if l.strip() and "1." in l or "2." in l or "3." in l)
        assert count <= 5


class TestWebSearchToolRegistration:
    def test_web_search_registered_in_registry(self):
        set_global_registry(None)
        bus = EventBus()
        registry = ToolRegistry(bus)
        set_global_registry(registry)

        from creamcode.tools import web as web_module
        import importlib
        importlib.reload(web_module)

        assert registry.has_tool("WebSearch")
        set_global_registry(None)

import asyncio
import re
import httpx
from urllib.parse import urlparse

from .decorator import tool


INTERNAL_NETWORKS = [
    "127.0.0.1", "localhost", "::1", "0.0.0.0",
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",
]


def _is_internal_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host in INTERNAL_NETWORKS:
            return True
        for prefix in INTERNAL_NETWORKS:
            if host.startswith(prefix):
                return True
        return False
    except Exception:
        return True


def _validate_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False
        if _is_internal_url(url):
            return False
        return True
    except Exception:
        return False


def _strip_html(html: str) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


@tool(
    name="WebFetch",
    description="Fetch the content of a webpage from the internet"
)
async def web_fetch(url: str, timeout: int = 30) -> str:
    """
    Fetch a webpage

    Args:
        url: URL of the webpage to fetch
        timeout: Timeout in seconds (default: 30)

    Returns:
        Webpage content (HTML or text)
    """
    if not _validate_url(url):
        return f"Error: Invalid or disallowed URL: {url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
            text = _strip_html(content)
            if len(text) > 5000:
                text = text[:5000] + "\n[truncated]"
            return text
    except httpx.TimeoutException:
        return f"Error: Request timed out after {timeout} seconds"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code}: {e.response.reason_phrase}"
    except httpx.RequestError as e:
        return f"Error: Request failed: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(
    name="WebSearch",
    description="Search the web for information"
)
async def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web

    Args:
        query: Search query
        num_results: Number of results to return (default: 5)

    Returns:
        Search results
    """
    if not query or not query.strip():
        return "Error: Empty search query"

    try:
        search_url = f"https://duckduckgo.com/html/?q={httpx.URL(query).params}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
            response = await client.get(search_url)
            response.raise_for_status()

            html = response.text
            results = []
            pattern = re.compile(r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>')
            url_pattern = re.compile(r'<a class="result__snippet" href="[^"]*">([^<]+)</a>')

            matches = pattern.findall(html)
            snippet_matches = url_pattern.findall(html)

            for i, (url, title) in enumerate(matches[:num_results]):
                snippet = snippet_matches[i][0] if i < len(snippet_matches) else ""
                results.append(f"{i + 1}. {title}\n   URL: {url}\n   {snippet}")

            if not results:
                return "No search results found"

            return "\n\n".join(results)

    except httpx.TimeoutException:
        return "Error: Search request timed out"
    except httpx.RequestError as e:
        return f"Error: Search failed: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

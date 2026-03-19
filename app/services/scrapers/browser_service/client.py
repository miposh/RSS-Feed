"""
HTTP client for Browser Service.
"""
import logging
import os
from typing import Optional

import httpx

from ..base import BaseScraper

logger = logging.getLogger(__name__)

# Default service URL (can be overridden via env)
BROWSER_SERVICE_URL = os.getenv("BROWSER_SERVICE_URL", "http://browser:8000")


class BrowserServiceClient(BaseScraper):
    """
    Client for centralized Browser Service.

    Connects to external Botasaurus service via HTTP API.
    Benefits:
        - No local Chromium in app container
        - Shared browser across multiple projects
        - Centralized memory management
        - Anti-detection features preserved
    """

    __slots__ = ("_base_url", "_timeout", "_client")

    def __init__(
        self,
        base_url: str = BROWSER_SERVICE_URL,
        timeout: int = 60
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "BrowserService"

    def is_available(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client

    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL via Browser Service."""
        try:
            client = await self._get_client()

            response = await client.post(
                "/fetch",
                json={"url": url, "timeout": self._timeout - 10}
            )
            response.raise_for_status()

            data = response.json()

            if data.get("success"):
                html = data.get("html")
                if html:
                    logger.debug(f"BrowserService returned {len(html)} bytes for {url}")
                    return html

            error = data.get("error", "Unknown error")
            logger.warning(f"BrowserService error for {url}: {error}")
            return None

        except httpx.TimeoutException:
            logger.warning(f"BrowserService timeout for {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"BrowserService HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"BrowserService error for {url}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if Browser Service is healthy."""
        try:
            client = await self._get_client()
            response = await client.get("/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    async def shutdown(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.info("BrowserService client closed")

"""
Botasaurus scraper implementation.
"""
from __future__ import annotations

import importlib.util
import logging
from functools import lru_cache
from typing import Any, Callable

from ..base import BaseScraper
from .request_queue import DEFAULT_REQUEST_DELAY, RequestQueue

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_fetch_html_func() -> Callable[[str], str] | None:
    """Lazy initialization of the browser-based fetch function."""
    try:
        from botasaurus.browser import Driver, browser
        
        @browser(
            reuse_driver=True,
            cache=True,
            block_images=True,
            max_retry=3,
            close_on_crash=True,
            output=None,
            create_error_logs=False,
        )
        def fetch_html_browser(driver: Driver, url: str) -> str:
            """
            Fetch HTML using Botasaurus browser with anti-detection.
            Results are cached automatically.
            """
            if driver.config.is_new:
                driver.google_get(url)
            else:
                driver.get(url)
            
            return driver.page_html
        
        return fetch_html_browser
        
    except ImportError:
        logger.exception("Failed to import botasaurus.browser")
        return None
    except Exception:
        logger.exception("Failed to initialize botasaurus browser function")
        return None


class BotasaurusScraper(BaseScraper):
    """
    Scraper using Botasaurus browser with anti-detection and caching.
    
    Features:
        - FIFO queue for rate-limited requests
        - Configurable delay between requests
        - Reuses browser driver for efficiency
        - Caches results to avoid re-fetching
        - Blocks images for speed
        - Auto-retry on failures
    """
    
    __slots__ = ("_available", "_request_delay", "_queue")
    
    def __init__(self, request_delay: float = DEFAULT_REQUEST_DELAY) -> None:
        self._available = self._check_availability()
        self._request_delay = request_delay
        self._queue: RequestQueue | None = None
    
    @staticmethod
    def _check_availability() -> bool:
        """Check if botasaurus is installed and available."""
        if importlib.util.find_spec("botasaurus") is None:
            logger.warning("botasaurus not installed")
            return False
        return True
    
    @property
    def name(self) -> str:
        return "Botasaurus"
    
    def is_available(self) -> bool:
        return self._available
    
    @property
    def request_delay(self) -> float:
        """Current delay between requests in seconds."""
        return self._request_delay
    
    @request_delay.setter
    def request_delay(self, value: float) -> None:
        """Update the delay between requests."""
        self._request_delay = value
        if self._queue is not None:
            self._queue.delay_seconds = value
    
    @property
    def pending_requests(self) -> int:
        """Number of requests waiting in queue."""
        return self._queue.pending_count if self._queue is not None else 0
    
    async def _get_queue(self) -> RequestQueue:
        """Get or initialize the request queue."""
        if self._queue is None:
            self._queue = await RequestQueue.get_instance(self._request_delay)
            
            fetch_func = _get_fetch_html_func()
            if fetch_func is not None:
                self._queue.fetch_func = fetch_func
        
        return self._queue
    
    async def fetch_html(self, url: str) -> str | None:
        """Fetch HTML content from URL."""
        if not self.is_available():
            logger.warning("Botasaurus not available")
            return None
        
        try:
            queue = await self._get_queue()
            
            if queue.fetch_func is None:
                logger.error("Botasaurus fetch function not initialized")
                return None
            
            logger.debug(
                "Enqueueing request for %s (queue size: %d)",
                url,
                queue.pending_count,
            )
            
            result = await queue.enqueue(url)
            
            return self._extract_html(result, url)
                
        except Exception:
            logger.exception("Botasaurus error fetching %s", url)
            return None
    
    @staticmethod
    def _extract_html(result: Any, url: str) -> str | None:
        """Extract HTML content from fetch result."""
        if not result:
            logger.warning("Botasaurus returned empty response for %s", url)
            return None
        
        html_content = result[0] if isinstance(result, list) else result
        
        if html_content:
            logger.debug(
                "Botasaurus returned %d bytes for %s",
                len(html_content),
                url,
            )
            return html_content
        
        logger.warning("Botasaurus returned empty response for %s", url)
        return None
    
    async def shutdown(self) -> None:
        """Shutdown the scraper and stop the request queue."""
        if self._queue is not None:
            await self._queue.stop()
            self._queue = None
            logger.info("Botasaurus scraper shutdown complete")

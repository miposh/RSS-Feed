"""
ScraperAPI scraper implementation.
Uses scraperapi-sdk to fetch web content through ScraperAPI service.
"""
import asyncio
import logging
from typing import Optional

from ..base import BaseScraper

logger = logging.getLogger(__name__)


class ScraperAPIScraper(BaseScraper):
    """Scraper using ScraperAPI service."""
    
    def __init__(self, api_key: str):
        """
        Initialize ScraperAPI scraper.
        
        Args:
            api_key: ScraperAPI API key
        """
        self._api_key = api_key
        self._client = None
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize the ScraperAPI client."""
        try:
            from scraperapi_sdk import ScraperAPIClient
            self._client = ScraperAPIClient(self._api_key)
            logger.debug("ScraperAPI client initialized")
        except ImportError:
            logger.error("scraperapi-sdk not installed")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to initialize ScraperAPI client: {e}")
            self._client = None
    
    @property
    def name(self) -> str:
        return "ScraperAPI"
    
    def is_available(self) -> bool:
        return self._client is not None and bool(self._api_key)
    
    async def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content using ScraperAPI with JavaScript rendering enabled.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string or None if fetch failed
        """
        if not self.is_available():
            logger.warning("ScraperAPI not available")
            return None
        
        try:
            logger.debug(f"Fetching via ScraperAPI with JS rendering: {url}")
            loop = asyncio.get_event_loop()
            html_content = await loop.run_in_executor(
                None,
                lambda: self._client.get(url=url, render=True)
            )
            
            if html_content:
                logger.debug(f"ScraperAPI returned {len(html_content)} bytes for {url}")
                return html_content
            else:
                logger.warning(f"ScraperAPI returned empty response for {url}")
                return None
                
        except Exception as e:
            logger.error(f"ScraperAPI error fetching {url}: {e}", exc_info=True)
            return None

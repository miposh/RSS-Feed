"""
Base scraper interface and common types.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ScraperType(str, Enum):
    """Available scraper types."""
    SCRAPERAPI = "scraperapi"
    BOTASAURUS = "botasaurus"


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the scraper name."""
        pass
    
    @abstractmethod
    async def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string or None if fetch failed
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the scraper is properly configured and available.
        
        Returns:
            True if scraper can be used, False otherwise
        """
        pass

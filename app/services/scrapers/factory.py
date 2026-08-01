"""
Scraper factory - creates scraper instances based on type.
"""
import logging
from typing import Optional

from .base import BaseScraper, ScraperType
from .scraperapi import ScraperAPIScraper
from .botasaurus import BotasaurusScraper
from .browser_service import BrowserServiceClient

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory for creating scraper instances."""
    
    @staticmethod
    def create(
        scraper_type: ScraperType,
        api_key: Optional[str] = None
    ) -> BaseScraper:
        """
        Create a scraper instance based on type.
        
        Args:
            scraper_type: Type of scraper to create
            api_key: API key (required for ScraperAPI)
            
        Returns:
            Scraper instance
            
        Raises:
            ValueError: If scraper type is unknown or required params missing
        """
        if scraper_type == ScraperType.SCRAPERAPI:
            if not api_key:
                raise ValueError("API key required for ScraperAPI")
            return ScraperAPIScraper(api_key)
        
        elif scraper_type == ScraperType.BOTASAURUS:
            return BotasaurusScraper()

        elif scraper_type == ScraperType.BROWSER_SERVICE:
            return BrowserServiceClient()

        else:
            raise ValueError(f"Unknown scraper type: {scraper_type}")


def get_scraper(
    scraper_type: ScraperType | str,
    api_key: Optional[str] = None
) -> BaseScraper:
    """
    Convenience function to get a scraper instance.
    
    Args:
        scraper_type: Type of scraper (ScraperType enum or string)
        api_key: API key (required for ScraperAPI)
        
    Returns:
        Scraper instance
    """
    if isinstance(scraper_type, str):
        scraper_type = ScraperType(scraper_type)
    
    return ScraperFactory.create(scraper_type, api_key)

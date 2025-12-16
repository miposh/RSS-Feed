"""
Scrapers module - provides different scraping backends for fetching web content.
"""
from .base import BaseScraper, ScraperType
from .factory import get_scraper, ScraperFactory

__all__ = [
    "BaseScraper",
    "ScraperType", 
    "get_scraper",
    "ScraperFactory",
]

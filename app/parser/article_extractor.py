"""
Article content extractor using ScraperAPI and newspaper4k.
Fetches full article content from URLs and extracts clean text.
"""
import asyncio
import logging
from typing import Optional

from scraperapi_sdk import ScraperAPIClient
from newspaper import Article, ArticleException
from config.config import config

logger = logging.getLogger(__name__)


class ArticleExtractor:
    """Extract article content using ScraperAPI and newspaper4k."""
    
    def __init__(self):
        """Initialize the article extractor with ScraperAPI client."""
        self.scraper_api_key = config.get("SCRAPER_API_KEY")
        self.scraper_enabled = config.get("SCRAPER_ENABLED", "false").lower() == "true"
        
        if self.scraper_enabled and not self.scraper_api_key:
            logger.warning("ScraperAPI включен, но API ключ не найден")
            self.scraper_enabled = False
        
        self.client = None
        if self.scraper_enabled:
            self.client = ScraperAPIClient(self.scraper_api_key)
            logger.info("ArticleExtractor инициализирован с ScraperAPI")
        else:
            logger.info("ArticleExtractor работает без ScraperAPI")
    
    async def extract_article_text(self, url: str) -> Optional[str]:
        """
        Extract article text from URL using ScraperAPI and newspaper4k.
        
        Args:
            url: The article URL to fetch and parse
            
        Returns:
            Extracted article text or None if extraction failed
        """
        try:
            # Fetch HTML content
            html_content = await self._fetch_html(url)
            if not html_content:
                logger.warning(f"Не удалось получить HTML для {url}")
                return None
            
            # Parse article with newspaper4k
            article_text = self._parse_article(html_content, url)
            if not article_text:
                logger.warning(f"Не удалось извлечь текст статьи для {url}")
                return None
            
            logger.info(f"Успешно извлечен текст статьи ({len(article_text)} символов) для {url}")
            return article_text
            
        except Exception as e:
            logger.error(f"Ошибка извлечения статьи {url}: {e}", exc_info=True)
            return None
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL using ScraperAPI if enabled, otherwise direct request.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string or None if fetch failed
        """
        try:
            if self.scraper_enabled and self.client:
                # Use ScraperAPI to fetch content (runs in thread pool as SDK is sync)
                logger.debug(f"Загрузка через ScraperAPI: {url}")
                loop = asyncio.get_event_loop()
                html_content = await loop.run_in_executor(
                    None, 
                    lambda: self.client.get(url=url)
                )
                
                if html_content:
                    return html_content
                else:
                    logger.warning(f"ScraperAPI вернул пустой ответ для {url}")
                    return None
            else:
                # Fallback to newspaper4k's built-in download
                logger.debug(f"Загрузка напрямую (без ScraperAPI): {url}")
                article = Article(url, language='ru')
                article.download()
                return article.html
                
        except Exception as e:
            logger.error(f"Ошибка загрузки HTML {url}: {e}", exc_info=True)
            return None
    
    def _parse_article(self, html: str, url: str) -> Optional[str]:
        """
        Parse article from HTML using newspaper4k.
        
        Args:
            html: HTML content as string
            url: Original article URL
            
        Returns:
            Extracted article text or None if parsing failed
        """
        try:
            # Create Article object with HTML
            article = Article(url, language='ru')
            
            # Download is skipped, we set html and html2text directly
            article.download_state = 2  # ArticleDownloadState.SUCCESS
            article.html = html
            
            # Parse the article
            article.parse()
            
            # Get the article text
            if article.text:
                return article.text.strip()
            else:
                logger.warning(f"newspaper4k не смог извлечь текст из {url}")
                return None
                
        except ArticleException as e:
            logger.error(f"Ошибка парсинга статьи newspaper4k для {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка парсинга для {url}: {e}", exc_info=True)
            return None


# Global instance
_article_extractor: Optional[ArticleExtractor] = None


def get_article_extractor() -> ArticleExtractor:
    """Get or create global ArticleExtractor instance."""
    global _article_extractor
    if _article_extractor is None:
        _article_extractor = ArticleExtractor()
    return _article_extractor


async def extract_article_content(url: str) -> Optional[str]:
    """
    Convenience function to extract article content from URL.
    
    Args:
        url: The article URL to fetch and parse
        
    Returns:
        Extracted article text or None if extraction failed
    """
    extractor = get_article_extractor()
    return await extractor.extract_article_text(url)

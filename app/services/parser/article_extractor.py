"""
Article content extractor using ScraperAPI and newspaper4k.
Fetches full article content from URLs and extracts clean text.
"""
import asyncio
import logging
from typing import Optional, List

from scraperapi_sdk import ScraperAPIClient
from scraperapi_sdk.exceptions import ScraperAPIException
from newspaper import Article, ArticleException
from config.config import get_config

logger = logging.getLogger(__name__)


class ArticleExtractor:
    """Extract article content using ScraperAPI and newspaper4k."""
    
    def __init__(self):
        """Initialize the article extractor with ScraperAPI client."""
        config = get_config()
        self.scraper_api_key = config.scraper.api_key
        self.scraper_enabled = config.scraper.enabled
        
        if self.scraper_enabled and not self.scraper_api_key:
            logger.warning("ScraperAPI включен, но API ключ не найден")
            self.scraper_enabled = False
        
        self.client = None
        if self.scraper_enabled:
            self.client = ScraperAPIClient(self.scraper_api_key)
            logger.info("ArticleExtractor инициализирован с ScraperAPI")
        else:
            logger.info("ArticleExtractor работает без ScraperAPI")
    
    async def extract_article_content(self, url: str) -> tuple[Optional[str], List[str]]:
        """
        Extract article text and images from URL using ScraperAPI and newspaper4k.
        
        Args:
            url: The article URL to fetch and parse
            
        Returns:
            Tuple of (text, image_urls). elements can be None or empty list.
        """
        try:
            # Fetch HTML content
            html_content = await self._fetch_html(url)
            if not html_content:
                logger.warning(f"Не удалось получить HTML для {url}")
                return None, []
            
            # Parse article with newspaper4k
            text, images = self._parse_article(html_content, url)
            if not text:
                logger.warning(f"Не удалось извлечь текст статьи для {url}")
                return None, images
            
            logger.info(f"Успешно извлечен текст ({len(text)} символов) и {len(images)} картинка (top_image) для {url}")
            return text, images
            
        except Exception as e:
            logger.error(f"Ошибка извлечения статьи {url}: {e}", exc_info=True)
            return None, []
    
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
                
                # Run synchronous download in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, article.download)
                
                return article.html
                
        except Exception as e:
            logger.error(f"Ошибка загрузки HTML {url}: {e}", exc_info=True)
            return None
    
    def _parse_article(self, html: str, url: str) -> tuple[Optional[str], List[str]]:
        """
        Parse article from HTML using newspaper4k.
        
        Args:
            html: HTML content as string
            url: Original article URL
            
        Returns:
            Tuple (text, list_of_image_urls)
        """
        try:
            # Create Article object with HTML
            article = Article(url, language='ru')
            
            # Download is skipped, we set html and html2text directly
            article.download_state = 2  # ArticleDownloadState.SUCCESS
            article.html = html
            
            # Parse the article
            article.parse()
            
            text = article.text.strip() if article.text else None

            # Extract only top_image if available
            images = []
            if article.top_image:
                images.append(article.top_image)

            return text, images
                
        except ArticleException as e:
            logger.error(f"Ошибка парсинга статьи newspaper4k для {url}: {e}")
            return None, []
        except Exception as e:
            logger.error(f"Неожиданная ошибка парсинга для {url}: {e}", exc_info=True)
            return None, []


# Global instance
_article_extractor: Optional[ArticleExtractor] = None


def get_article_extractor() -> ArticleExtractor:
    """Get or create global ArticleExtractor instance."""
    global _article_extractor
    if _article_extractor is None:
        _article_extractor = ArticleExtractor()
    return _article_extractor


async def extract_article_content(url: str, api_key: Optional[str] = None) -> tuple[Optional[str], List[str]]:
    """
    Convenience function to extract article content and images from URL.
    
    Args:
        url: The article URL to fetch and parse
        api_key: Optional custom ScraperAPI key (uses global config if None)
        
    Returns:
        Tuple (text, image_urls)
    """
    if api_key:
        # Create a temporary extractor with custom API key
        try:
            from scraperapi_sdk import ScraperAPIClient
            client = ScraperAPIClient(api_key)
            
            # Fetch HTML with custom client
            loop = asyncio.get_event_loop()
            html_content = await loop.run_in_executor(
                None, 
                lambda: client.get(url=url)
            )
            
            if not html_content:
                logger.warning(f"ScraperAPI вернул пустой ответ для {url}")
                return None, []
            
            # Parse with newspaper4k
            from newspaper import Article
            article = Article(url, language='ru')
            article.download_state = 2  # ArticleDownloadState.SUCCESS
            article.html = html_content
            article.parse()
            
            text = article.text.strip() if article.text else None

            # Extract only top_image if available
            images = []
            if article.top_image:
                images.append(article.top_image)

            if text:
                logger.info(f"Успешно извлечен текст ({len(text)} символов) для {url} с custom API key")
                return text, images
            else:
                logger.warning(f"newspaper4k не смог извлечь текст из {url}")
                return None, images
        
        except ScraperAPIException as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning(f"ScraperAPI Forbidden (403) for {url} with custom key. Check API key.")
            else:
                logger.warning(f"ScraperAPI error for {url}: {e}")
            return None, []
            
        except Exception as e:
            logger.error(f"Ошибка извлечения статьи с custom API key {url}: {e}", exc_info=True)
            return None, []
    else:
        # Use global extractor
        extractor = get_article_extractor()
        return await extractor.extract_article_content(url)

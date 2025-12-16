"""
Article content extractor using configurable scrapers and newspaper4k.
Fetches full article content from URLs and extracts clean text.
"""
import logging
from typing import Optional, List

from newspaper import Article, ArticleException

from app.services.scrapers import BaseScraper, ScraperType, get_scraper

logger = logging.getLogger(__name__)


class ArticleExtractor:
    """Extract article content using configurable scrapers and newspaper4k."""
    
    def __init__(
        self,
        scraper_type: ScraperType = ScraperType.BOTASAURUS,
        api_key: Optional[str] = None
    ):
        """
        Initialize the article extractor with specified scraper.
        
        Args:
            scraper_type: Type of scraper to use
            api_key: API key (required for ScraperAPI)
        """
        self.scraper_type = scraper_type
        self.api_key = api_key
        self._scraper: Optional[BaseScraper] = None
        
        self._init_scraper()
    
    def _init_scraper(self) -> None:
        """Initialize the scraper based on type."""
        try:
            self._scraper = get_scraper(self.scraper_type, self.api_key)
            if self._scraper.is_available():
                logger.info(f"ArticleExtractor инициализирован с {self._scraper.name}")
            else:
                logger.warning(f"{self._scraper.name} недоступен, используется Botasaurus")
                self._scraper = get_scraper(ScraperType.BOTASAURUS)
        except ValueError as e:
            logger.warning(f"Ошибка инициализации скрапера: {e}, используется Botasaurus")
            self._scraper = get_scraper(ScraperType.BOTASAURUS)
    
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
        Fetch HTML content from URL using configured scraper.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string or None if fetch failed
        """
        if self._scraper is None:
            logger.error("Scraper не инициализирован")
            return None
        
        return await self._scraper.fetch_html(url)
    
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
            # Create Article object - let newspaper4k auto-detect language
            article = Article(url)
            
            # Use proper method to load pre-fetched HTML
            article.download(input_html=html)
            article.parse()
            
            detected_lang = getattr(article, 'meta_lang', None) or 'auto'
            logger.debug(f"Detected language for {url}: {detected_lang}")
            
            text = article.text.strip() if article.text else None

            # Extract top_image
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


# Cache extractors by (scraper_type, api_key) to reuse scrapers and FIFO queue
_extractor_cache: dict[tuple[str, Optional[str]], ArticleExtractor] = {}


def _get_cached_extractor(
    scraper_type: ScraperType,
    api_key: Optional[str] = None
) -> ArticleExtractor:
    """Get or create cached ArticleExtractor instance."""
    cache_key = (scraper_type.value, api_key)
    
    if cache_key not in _extractor_cache:
        _extractor_cache[cache_key] = ArticleExtractor(
            scraper_type=scraper_type,
            api_key=api_key
        )
        logger.debug(f"Created new ArticleExtractor for {scraper_type.value}")
    
    return _extractor_cache[cache_key]


async def extract_article_content(
    url: str,
    scraper_type: ScraperType | str = ScraperType.BOTASAURUS,
    api_key: Optional[str] = None
) -> tuple[Optional[str], List[str]]:
    """
    Convenience function to extract article content and images from URL.
    
    Uses cached extractors to ensure all requests go through the same
    FIFO queue with proper rate limiting.
    
    Args:
        url: The article URL to fetch and parse
        scraper_type: Type of scraper to use (ScraperType enum or string)
        api_key: API key (required for ScraperAPI)
        
    Returns:
        Tuple (text, image_urls)
    """
    if isinstance(scraper_type, str):
        try:
            scraper_type = ScraperType(scraper_type)
        except ValueError:
            logger.warning(f"Unknown scraper type: {scraper_type}, using BOTASAURUS")
            scraper_type = ScraperType.BOTASAURUS
    
    extractor = _get_cached_extractor(scraper_type, api_key)
    return await extractor.extract_article_content(url)

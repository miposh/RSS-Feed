import logging
from urllib.parse import urlparse
from typing import Tuple, Optional

from fetcher.http_client import get_http_client
from parser.rss_parser import parse_rss_feed

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        if result.scheme not in ('http', 'https'):
            return False
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False


async def validate_rss_feed(url: str) -> Tuple[bool, Optional[str]]:
    if not is_valid_url(url):
        return False, "Invalid URL format"
    
    try:
        async with get_http_client() as http_client:
            content_bytes, status, error = await http_client.fetch(
                url,
                use_cache=False,
                verify_ssl=False
            )
        
        if status == 403:
            return False, "HTTP error: 403 (Forbidden) - Сайт блокирует автоматические запросы. Попробуйте другую RSS-ленту или обратитесь к администратору сайта."
        
        if status != 200 or content_bytes is None:
            return False, f"HTTP error: {status} - {error}"
        
        posts = await parse_rss_feed(content_bytes)
        
        if posts is None:
            return False, "Failed to parse feed - invalid format or malformed XML"
        
        return True, None
        
    except Exception as e:
        logger.error(f"RSS validation error: {e}", exc_info=True)
        return False, f"Validation error: {str(e)}" 
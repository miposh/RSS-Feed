import logging
from urllib.parse import urlparse
import feedparser
import requests
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        # Check that scheme is either http or https
        if result.scheme not in ('http', 'https'):
            return False
        # Check that netloc is not empty
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False


async def validate_rss_feed(url: str) -> Tuple[bool, Optional[str]]:
    if not is_valid_url(url):
        return False, "Invalid URL format"
    
    try:
        # Create a session with browser-like headers to avoid blocking
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Use requests with streaming mode to handle chunked transfer encoding issues
        response = session.get(
            url, 
            timeout=10, 
            verify=False,
            stream=True  # Use streaming mode
        )
        
        if response.status_code != 200:
            return False, f"HTTP error: {response.status_code}"
        
        # Read content in chunks to avoid transfer encoding issues
        content_bytes = b""
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
            if chunk:
                content_bytes += chunk
        
        # Decode the content with proper encoding handling
        try:
            content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Try alternative encodings if UTF-8 fails
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    content = content_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # If all encodings fail, use errors='replace'
                content = content_bytes.decode('utf-8', errors='replace')
                
        feed = feedparser.parse(content)
        
        # Allow feeds with minor parsing issues (bozo bit) but reject critical errors
        if feed.bozo and feed.bozo_exception:
            # Only reject on critical parsing errors, not minor XML issues
            error_str = str(feed.bozo_exception).lower()
            if any(critical in error_str for critical in ['not well-formed', 'syntax error', 'mismatched tag']):
                return False, f"Feed parsing error: {feed.bozo_exception}"
            else:
                logger.warning(f"Feed has minor parsing issues but is usable: {feed.bozo_exception}")
            
        if not hasattr(feed, 'feed') or not hasattr(feed, 'entries'):
            return False, "Invalid feed format"
            
        return True, None
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {e}"
    except Exception as e:
        logger.error(f"RSS validation error: {e}")
        return False, f"Validation error: {str(e)}" 
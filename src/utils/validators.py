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
        # Create a session with custom headers to avoid chunked transfer encoding issues
        session = requests.Session()
        session.headers.update({'Accept-Encoding': 'identity'})  # Disable compression
        
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
        content = ""
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if chunk:
                content += chunk
                
        feed = feedparser.parse(content)
        
        if feed.bozo and feed.bozo_exception:
            return False, f"Feed parsing error: {feed.bozo_exception}"
            
        if not hasattr(feed, 'feed') or not hasattr(feed, 'entries'):
            return False, "Invalid feed format"
            
        return True, None
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {e}"
    except Exception as e:
        logger.error(f"RSS validation error: {e}")
        return False, f"Validation error: {str(e)}" 
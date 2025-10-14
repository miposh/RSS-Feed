"""
RSS feed parser with encoding detection and error handling.
"""
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

import feedparser
from models.rss_post import RSSPost

logger = logging.getLogger(__name__)


class RSSParser:
    """Parser for RSS/Atom feeds."""
    
    @staticmethod
    def decode_content(content_bytes: bytes) -> str:
        """
        Decode feed content with fallback encodings.
        
        Args:
            content_bytes: Raw feed content
        
        Returns:
            Decoded string content
        """
        # Try UTF-8 first
        try:
            return content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
        
        # Fallback encodings
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                return content_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # Last resort: replace errors
        logger.warning(
            "Failed to decode with known encodings, using replacement",
            extra={"size_bytes": len(content_bytes)}
        )
        return content_bytes.decode('utf-8', errors='replace')
    
    @staticmethod
    def parse_feed(content: str) -> Optional[feedparser.FeedParserDict]:
        """
        Parse RSS/Atom feed from string content.
        
        Args:
            content: Feed content as string
        
        Returns:
            Parsed feed data or None on error
        """
        try:
            feed_data = feedparser.parse(content)
            
            # Check for critical parsing errors
            if feed_data.bozo and feed_data.bozo_exception:
                error_str = str(feed_data.bozo_exception).lower()
                critical_errors = ['not well-formed', 'syntax error', 'mismatched tag']
                
                if any(err in error_str for err in critical_errors):
                    logger.error(
                        "Critical feed parsing error",
                        extra={"error": str(feed_data.bozo_exception)}
                    )
                    return None
                else:
                    logger.warning(
                        "Minor feed parsing issue",
                        extra={"error": str(feed_data.bozo_exception)}
                    )
            
            # Validate feed structure
            if not hasattr(feed_data, 'entries'):
                logger.error("Feed has no entries attribute")
                return None
            
            return feed_data
        
        except Exception as e:
            logger.error(
                f"Unexpected parsing error: {e}",
                exc_info=True
            )
            return None
    
    @staticmethod
    def extract_posts(feed_data: feedparser.FeedParserDict) -> List[RSSPost]:
        """
        Extract posts from parsed feed data.
        
        Args:
            feed_data: Parsed feed data from feedparser
        
        Returns:
            List of RSSPost objects
        """
        posts = []
        
        for entry in feed_data.entries:
            try:
                post = RSSParser._parse_entry(entry)
                posts.append(post)
            except Exception as e:
                logger.warning(
                    f"Failed to parse entry: {e}",
                    extra={"entry_title": getattr(entry, 'title', 'Unknown')},
                    exc_info=True
                )
                continue
        
        return posts
    
    @staticmethod
    def _parse_entry(entry) -> RSSPost:
        """
        Parse a single feed entry into RSSPost.
        
        Args:
            entry: Feed entry from feedparser
        
        Returns:
            RSSPost object
        """
        # Extract GUID (prefer guid > id > link)
        entry_id = getattr(entry, 'guid', getattr(entry, 'id', entry.link))
        
        # Extract basic fields
        title = getattr(entry, 'title', 'No title')
        link = getattr(entry, 'link', '')
        summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
        
        # Parse published time
        published_time = RSSParser._parse_published_time(entry)
        
        return RSSPost(
            guid=entry_id,
            title=title,
            link=link,
            summary=summary,
            published_time=published_time
        )
    
    @staticmethod
    def _parse_published_time(entry) -> Optional[datetime]:
        """
        Extract and parse published time from entry.
        
        Args:
            entry: Feed entry
        
        Returns:
            Datetime in UTC+3 timezone or None
        """
        # Try published_parsed first
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                # Create datetime in UTC
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                # Convert to UTC+3
                return dt.astimezone(timezone(timedelta(hours=3)))
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse published_parsed: {e}")
        
        # Fallback to updated_parsed
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                return dt.astimezone(timezone(timedelta(hours=3)))
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse updated_parsed: {e}")
        
        return None


async def parse_rss_feed(content_bytes: bytes) -> Optional[List[RSSPost]]:
    """
    High-level function to parse RSS feed from bytes.
    
    Args:
        content_bytes: Raw feed content
    
    Returns:
        List of RSSPost objects or None on error
    """
    # Decode content
    content = RSSParser.decode_content(content_bytes)
    
    # Parse feed
    feed_data = RSSParser.parse_feed(content)
    if not feed_data:
        return None
    
    # Check if feed has entries
    if not feed_data.entries:
        logger.warning("Feed has no entries")
        return []
    
    # Extract posts
    posts = RSSParser.extract_posts(feed_data)
    
    logger.info(
        "Feed parsed successfully",
        extra={
            "entries_count": len(feed_data.entries),
            "posts_extracted": len(posts)
        }
    )
    
    return posts

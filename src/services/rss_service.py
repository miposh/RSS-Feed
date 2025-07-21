import feedparser
import logging
import asyncio
import requests
from datetime import datetime
import ssl

from aiogram import Bot

from services.rss_management_service import RSSManagementService
from models.rss_post import RSSPost
from config.config import config

logger = logging.getLogger(__name__)

# Get constants from config
RSS_CHECK_INTERVAL = config.get("RSS_CHECK_INTERVAL", 300)  # Default: 5 minutes
POST_AGE_LIMIT = config.get("POST_AGE_LIMIT", 86400)  # Default: 24 hours


class RSSService:
    def __init__(self, bot: Bot, rss_management_service: RSSManagementService):
        
        self.bot = bot
        self.rss_management_service = rss_management_service
        self.check_interval = int(RSS_CHECK_INTERVAL)
        self.post_age_limit = int(POST_AGE_LIMIT)
        self.running = False
        self.task = None
        
        # Configure SSL context for legacy servers
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def start(self) -> None:
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._check_feeds_loop())
        logger.info("RSS feed service started")

    async def stop(self) -> None:
        if not self.running:
            return
            
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("RSS feed service stopped")

    async def _check_feeds_loop(self) -> None:
        while self.running:
            try:
                await self._check_all_feeds()
            except Exception as e:
                logger.error(f"Error checking feeds: {e}", exc_info=True)
                
            # Wait for next check interval
            await asyncio.sleep(self.check_interval)

    async def _check_all_feeds(self) -> None:
        feeds = await self.rss_management_service.get_all_feeds()
        if not feeds:
            logger.info("No RSS feeds to check")
            return
            
        logger.info(f"Checking {len(feeds)} RSS feeds")
        
        for feed_id, feed_url, chat_id in feeds:
            try:
                await self._process_feed(feed_id, feed_url, chat_id)
            except Exception as e:
                logger.error(f"Error processing feed {feed_url}: {e}", exc_info=True)

    async def _process_feed(self, feed_id: int, feed_url: str, chat_id: int) -> None:
        logger.info(f"Processing feed {feed_url} for chat {chat_id}")
        
        try:
            # Create a session with custom headers to avoid chunked transfer encoding issues
            session = requests.Session()
            session.headers.update({'Accept-Encoding': 'identity'})  # Disable compression
            
            # Use requests with streaming mode to handle chunked transfer encoding issues
            response = session.get(
                feed_url, 
                timeout=30, 
                verify=False,
                stream=True  # Use streaming mode
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch feed {feed_url}: HTTP {response.status_code}")
                return
            
            # Read content in chunks to avoid transfer encoding issues
            content = ""
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    content += chunk
                    
            feed_data = feedparser.parse(content)
            
            if not feed_data.entries:
                logger.warning(f"No entries in feed {feed_url}")
                return
            
            # Process in reverse order to send oldest first
            for entry in reversed(feed_data.entries):
                post = self._parse_entry(entry)
                await self._process_post(post, feed_id, chat_id)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching feed {feed_url}: {e}")
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}", exc_info=True)
    
    def _parse_entry(self, entry) -> RSSPost:
        # Use the entry's guid/id or link as unique identifier
        entry_id = getattr(entry, 'guid', getattr(entry, 'id', entry.link))
        title = getattr(entry, 'title', 'No title')
        link = getattr(entry, 'link', '')
        summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
        
        # Try to get the publication date
        published_time = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published_time = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published_time = datetime(*entry.updated_parsed[:6])
        
        return RSSPost(
            guid=entry_id,
            title=title,
            link=link,
            summary=summary,
            published_time=published_time
        )
    
    async def _process_post(self, post: RSSPost, feed_id: int, chat_id: int) -> None:
        # Check if we've already sent this post
        if await self.rss_management_service.is_post_sent(post.guid, feed_id):
            return
        
        # Check if the post is too old
        current_time = datetime.now()
        if post.published_time and (current_time - post.published_time).total_seconds() > self.post_age_limit:
            # Mark the post as sent to avoid checking it again
            await self.rss_management_service.mark_post_as_sent(post.guid, feed_id)
            logger.info(f"Skipping old post from feed {feed_id}: {post.title}")
            return
            
        # Format the post message
        message = self._format_post_message(post)
        
        try:
            # Send the message to the chat
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                disable_web_page_preview=False
            )
            
            # Mark the post as sent
            await self.rss_management_service.mark_post_as_sent(post.guid, feed_id)
            logger.info(f"Sent new post from feed {feed_id} to chat {chat_id}: {post.title}")
            
        except Exception as e:
            logger.error(f"Error sending post to chat {chat_id}: {e}", exc_info=True)
    
    def _format_post_message(self, post: RSSPost) -> str:
        message = f"<b>{post.title}</b>\n\n"
        
        if post.summary:
            # Limit summary length
            if len(post.summary) > 300:
                summary = post.summary[:297] + "..."
            else:
                summary = post.summary
            message += f"{summary}\n\n"
            
        if post.link:
            message += f"<a href='{post.link}'>Читать полностью</a>\n\n"
            
        if post.published_time:
            message += f"<i>📅 {post.published_time.strftime('%Y-%m-%d %H:%M')}</i>"
            
        return message 
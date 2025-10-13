import feedparser
import logging
import asyncio
import requests
import re
from datetime import datetime, timedelta, timezone
import ssl
from collections import defaultdict, deque
from typing import Dict, Deque

from aiogram import Bot

from services.rss_management_service import RSSManagementService
from models.rss_post import RSSPost
from config.config import config

logger = logging.getLogger(__name__)

RSS_CHECK_INTERVAL = config.get("RSS_CHECK_INTERVAL")
SENT_POSTS_RETENTION_DAYS = int(config.get("SENT_POSTS_RETENTION_DAYS", 30))
CLEANUP_INTERVAL = int(config.get("CLEANUP_INTERVAL", 86400))

class RSSService:
    def __init__(self, bot: Bot, rss_management_service: RSSManagementService):
        
        self.bot = bot
        self.rss_management_service = rss_management_service
        self.check_interval = int(RSS_CHECK_INTERVAL)
        self.running = False
        self.task = None
        self.cleanup_task = None
        
        self.message_timestamps: Dict[int, Deque[datetime]] = defaultdict(deque)
        self.max_messages_per_minute_per_group = 20
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def start(self) -> None:
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._check_feeds_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
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
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
                
        logger.info("RSS feed service stopped")

    async def _check_feeds_loop(self) -> None:
        while self.running:
            try:
                await self._check_all_feeds()
            except Exception as e:
                logger.error(f"Error checking feeds: {e}", exc_info=True)
                
            await asyncio.sleep(self.check_interval)
            
    async def _cleanup_loop(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                
                deleted_count = await self.rss_management_service.cleanup_old_sent_posts(SENT_POSTS_RETENTION_DAYS)
                logger.info(f"Scheduled cleanup completed: removed {deleted_count} old sent posts")
            except Exception as e:
                logger.error(f"Error during cleanup task: {e}", exc_info=True)

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
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = session.get(
                        feed_url, 
                        timeout=(10, 30), 
                        verify=False,
                        stream=True
                    )
                    
                    if response.status_code == 403:
                        logger.warning(f"Failed to fetch feed {feed_url}: HTTP 403 (Forbidden) - Site is blocking automated requests")
                        return
                    elif response.status_code != 200:
                        logger.warning(f"Failed to fetch feed {feed_url}: HTTP {response.status_code}")
                        return
                    
                    content_bytes = b""
                    for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
                        if chunk:
                            content_bytes += chunk
                    
                    break
                    
                except (requests.exceptions.ChunkedEncodingError, 
                        requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to fetch feed {feed_url} after {max_retries} attempts: {e}")
                        return
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed for feed {feed_url}: {e}. Retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
            
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        content = content_bytes.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    content = content_bytes.decode('utf-8', errors='replace')
                    
            feed_data = feedparser.parse(content)
            
            if not feed_data.entries:
                logger.warning(f"No entries in feed {feed_url}")
                return
            
            for entry in reversed(feed_data.entries):
                post = self._parse_entry(entry)
                await self._process_post(post, feed_id, chat_id)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching feed {feed_url}: {e}")
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}", exc_info=True)
    
    def _parse_entry(self, entry) -> RSSPost:
        entry_id = getattr(entry, 'guid', getattr(entry, 'id', entry.link))
        title = getattr(entry, 'title', 'No title')
        link = getattr(entry, 'link', '')
        summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
        
        published_time = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            published_time = published_time.astimezone(timezone(timedelta(hours=3)))
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            # Create datetime in UTC
            published_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            # Convert to UTC+3
            published_time = published_time.astimezone(timezone(timedelta(hours=3)))
        
        return RSSPost(
            guid=entry_id,
            title=title,
            link=link,
            summary=summary,
            published_time=published_time
        )
    
    async def _process_post(self, post: RSSPost, feed_id: int, chat_id: int) -> None:
        if await self.rss_management_service.is_post_sent(post.guid, feed_id):
            return
        
        has_sent_posts = await self.rss_management_service.has_sent_posts_for_feed(feed_id)
        if not has_sent_posts:
            logger.info(f"New feed {feed_id}: marking existing post as sent without sending: {post.title}")
            await self.rss_management_service.mark_post_as_sent(post.guid, feed_id)
            return
        
        if not self._can_send_message(chat_id):
            logger.warning(f"Anti-flood: skipping message to group {chat_id}, rate limit exceeded (max {self.max_messages_per_minute_per_group}/min per group)")
            await self.rss_management_service.mark_post_as_sent(post.guid, feed_id)
            return
        
        message = self._format_post_message(post)
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                disable_web_page_preview=False
            )
            
            self._track_sent_message(chat_id)
            
            await self.rss_management_service.mark_post_as_sent(post.guid, feed_id)
            logger.info(f"Sent new post from feed {feed_id} to chat {chat_id}: {post.title}")
            
        except Exception as e:
            logger.error(f"Error sending post to chat {chat_id}: {e}", exc_info=True)
    
    def _format_post_message(self, post: RSSPost) -> str:
        message = f"<b>{self._clean_html_tags(post.title)}</b>\n\n"
        
        if post.summary:
            clean_summary = self._clean_html_tags(post.summary)
            
            if len(clean_summary) > 300:
                summary = clean_summary[:297] + "..."
            else:
                summary = clean_summary
            message += f"{summary}\n\n"
            
        if post.link:
            message += f"<a href='{post.link}'>Читать полностью</a>\n\n"
            
        if post.published_time:
            message += f"<i>📅 {post.published_time.strftime('%Y-%m-%d %H:%M')}</i>"
            
        return message
    
    def _clean_html_tags(self, text: str) -> str:
        """Remove unsupported HTML tags and clean text for Telegram"""
        if not text:
            return ""
        
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&apos;', "'")
        text = text.replace('&nbsp;', ' ')
        
        text = re.sub(r'<[^>]+>', '', text)
        
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _can_send_message(self, chat_id: int) -> bool:
        now = datetime.now()
        timestamps = self.message_timestamps[chat_id]
        
        while timestamps and (now - timestamps[0]) > timedelta(minutes=1):
            timestamps.popleft()
        
        return len(timestamps) < self.max_messages_per_minute_per_group
    
    def _track_sent_message(self, chat_id: int) -> None:
        now = datetime.now()
        self.message_timestamps[chat_id].append(now)
import logging
import asyncio
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from typing import Dict, Deque

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.database.db import DB
from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from config.config import get_config
from app.services.fetcher.http_client import get_http_client, close_http_client
from app.services.parser.rss_parser import parse_rss_feed
from app.services.parser.models import RSSPost

logger = logging.getLogger(__name__)

_config = get_config()
RSS_CHECK_INTERVAL = _config.rss.check_interval
CLEANUP_INTERVAL = _config.rss.cleanup_interval


class NewRSSService:
    """Service for fetching and distributing RSS feeds."""
    
    def __init__(self, bot: Bot, db_pool: AsyncConnectionPool):
        self.bot = bot
        self.db_pool = db_pool
        self.check_interval = int(RSS_CHECK_INTERVAL)
        self.running = False
        self.task = None
        self.cleanup_task = None
        
        # Rate limiting for Telegram
        self.message_timestamps: Dict[int, Deque[datetime]] = defaultdict(deque)
        self.max_messages_per_minute_per_group = 20
    
    async def start(self) -> None:
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._check_feeds_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("RSS feed service started (parsing news from last 1 hour)")
    
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
        
        await close_http_client()
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
                await self._cleanup_old_data()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    async def _check_all_feeds(self) -> None:
        """Check all feeds that need to be fetched."""
        async with self.db_pool.connection() as raw_connection:
            async with raw_connection.transaction():
                connection = PsycopgConnection(raw_connection)
                db = DB(connection)
                
                active_feeds = await db.rss_feeds.get_feeds_to_fetch()
                
                if not active_feeds:
                    logger.debug("No active feeds to check")
                    return
                
                logger.info(f"Checking {len(active_feeds)} active feeds")
                
                for feed in active_feeds:
                    try:
                        await self._process_feed(
                            db=db,
                            feed_id=feed.id,
                            feed_url=feed.url,
                            last_modified=feed.last_modified,
                            etag=feed.etag
                        )
                    except Exception as e:
                        logger.error(f"Error processing feed {feed.url}: {e}", exc_info=True)
    
    async def _process_feed(
        self,
        db: DB,
        feed_id: int,
        feed_url: str,
        last_modified: str = None,
        etag: str = None
    ) -> None:
        """Process a single RSS feed."""
        logger.debug(f"Processing feed {feed_url}")
        
        try:
            async with get_http_client() as http_client:
                content_bytes, status, error = await http_client.fetch(
                    feed_url,
                    use_cache=True,
                    verify_ssl=False
                )
            
            if status == 304:
                logger.debug(f"Feed not modified: {feed_url}")
                return
            
            if content_bytes is None:
                logger.warning(f"Failed to fetch feed {feed_url}: {error}")
                await db.rss_feeds.update_error_count(feed_id=feed_id)
                return
            
            posts = await parse_rss_feed(content_bytes)
            if not posts:
                logger.debug(f"No posts in feed {feed_url}")
                return
            
            # Get channel IDs subscribed to this feed
            channel_ids = await db.feed_subscriptions.get_channels_for_feed(feed_id=feed_id)
            if not channel_ids:
                logger.debug(f"No active subscriptions for feed {feed_id}")
                return
            
            for post in posts:
                # Пропускаем новости старше 1 часа
                if post.published_time:
                    utc_plus_3 = timezone(timedelta(hours=3))
                    now = datetime.now(utc_plus_3)
                    one_hour_ago = now - timedelta(hours=1)
                    
                    if post.published_time < one_hour_ago:
                        logger.debug(
                            f"Пропускаем старую новость (>1ч): {post.title[:50]} "
                            f"(опубликована {post.published_time.strftime('%Y-%m-%d %H:%M')})"
                        )
                        continue
                
                await self._process_post(post, feed_id, channel_ids)
            
            # Update feed metadata
            await db.rss_feeds.update_fetch_status(
                feed_id=feed_id,
                last_status=status,
                etag=None,
                last_modified=None
            )
            
            # Reset error count on successful fetch
            await db.rss_feeds.reset_error_count(feed_id=feed_id)
            
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}", exc_info=True)
    
    async def _process_post(
        self,
        post: RSSPost,
        feed_id: int,
        chat_telegram_ids: list
    ) -> None:
        # Note: ScraperAPI is now handled per-channel in ChannelRSSWorker
        # This legacy service doesn't use scraper
        
        message = await self._format_post_message(post)
        
        for chat_telegram_id in chat_telegram_ids:
            if not self._can_send_message(chat_telegram_id):
                logger.warning(f"Rate limit exceeded for chat {chat_telegram_id}")
                continue
            
            try:
                await self.bot.send_message(
                    chat_id=chat_telegram_id,
                    text=message,
                    disable_web_page_preview=False
                )
                
                self._track_sent_message(chat_telegram_id)
                logger.info(f"Sent post to chat {chat_telegram_id}: {post.title[:50]}")
                
            except TelegramBadRequest as e:
                if "chat not found" in str(e).lower():
                    logger.warning(
                        f"Chat {chat_telegram_id} not found. Consider removing."
                    )
                else:
                    logger.error(f"Bad request for chat {chat_telegram_id}: {e}")
            
            except TelegramForbiddenError:
                logger.warning(f"Bot forbidden in chat {chat_telegram_id}")
            
            except Exception as e:
                logger.error(f"Error sending to chat {chat_telegram_id}: {e}")
    
    async def _format_post_message(self, post: RSSPost) -> str:
        def clean_html(text: str) -> str:
            if not text:
                return ""
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&nbsp;', ' ')
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        message = f"<b>{clean_html(post.title)}</b>\n\n"
        
        # Use content if available, otherwise fall back to summary
        text_to_use = post.content if post.content else post.summary
        
        if text_to_use:
            clean_text = clean_html(text_to_use)
            
            # Limit to 4080 characters as requested
            max_text_length = 4080
            # Reserve space for title, link, and timestamp (approx 150 chars)
            max_content_length = max_text_length - len(message) - 150
            
            if len(clean_text) > max_content_length:
                text = clean_text[:max_content_length - 3] + "..."
            else:
                text = clean_text
            message += f"{text}\n\n"
        
        if post.link:
            message += f"<a href='{post.link}'>Читать полностью</a>\n\n"
        
        if post.published_time:
            message += f"<i>📅 {post.published_time.strftime('%Y-%m-%d %H:%M')}</i>"
        
        return message
    
    def _can_send_message(self, chat_id: int) -> bool:
        now = datetime.now()
        timestamps = self.message_timestamps[chat_id]
        
        while timestamps and (now - timestamps[0]) > timedelta(minutes=1):
            timestamps.popleft()
        
        return len(timestamps) < self.max_messages_per_minute_per_group
    
    def _track_sent_message(self, chat_id: int) -> None:
        self.message_timestamps[chat_id].append(datetime.now())
    
    async def _cleanup_old_data(self) -> None:
        logger.debug("Cleanup task executed")

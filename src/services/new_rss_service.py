import logging
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, Deque

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from services.chat_service import ChatService
from models.rss_post import RSSPost
from config.config import config
from fetcher.http_client import get_http_client, close_http_client
from parser.rss_parser import parse_rss_feed
from repositories.feed_repository import FeedRepository
from repositories.chat_repository import ChatRepository
from repositories.subscription_repository import SubscriptionRepository

logger = logging.getLogger(__name__)

RSS_CHECK_INTERVAL = config.get("RSS_CHECK_INTERVAL", 300)
CLEANUP_INTERVAL = int(config.get("CLEANUP_INTERVAL", 86400))


class NewRSSService:
    def __init__(self, bot: Bot, chat_service: ChatService):
        self.bot = bot
        self.chat_service = chat_service
        self.check_interval = int(RSS_CHECK_INTERVAL)
        self.running = False
        self.task = None
        self.cleanup_task = None
        
        # Repositories
        self.feed_repo = FeedRepository(config.db_path)
        self.chat_repo = ChatRepository(config.db_path)
        self.sub_repo = SubscriptionRepository(config.db_path)
        
        # Rate limiting for Telegram
        self.message_timestamps: Dict[int, Deque[datetime]] = defaultdict(deque)
        self.max_messages_per_minute_per_group = 20
    
    async def start(self) -> None:
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._check_feeds_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("RSS feed service started with new schema")
    
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
        active_feeds = await self.feed_repo.get_active_feeds()
        
        if not active_feeds:
            logger.debug("No active feeds to check")
            return
        
        logger.info(f"Checking {len(active_feeds)} active feeds")
        
        for feed in active_feeds:
            feed_id, url, title, last_modified, etag, pull_interval = feed
            try:
                await self._process_feed(feed_id, url, last_modified, etag)
            except Exception as e:
                logger.error(f"Error processing feed {url}: {e}", exc_info=True)
    
    async def _process_feed(
        self,
        feed_id: int,
        feed_url: str,
        last_modified: str = None,
        etag: str = None
    ) -> None:
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
                return
            
            posts = await parse_rss_feed(content_bytes)
            if not posts:
                logger.debug(f"No posts in feed {feed_url}")
                return
            
            chat_ids = await self.sub_repo.get_chats_for_feed(feed_id)
            if not chat_ids:
                logger.debug(f"No active subscriptions for feed {feed_id}")
                return
            
            for post in posts:
                await self._process_post(post, feed_id, chat_ids)
            
            await self.feed_repo.update_feed_metadata(
                feed_id=feed_id,
                title=posts[0].title if posts else None,
                last_modified=None,  
                etag=None 
            )
            
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}", exc_info=True)
    
    async def _process_post(
        self,
        post: RSSPost,
        feed_id: int,
        chat_telegram_ids: list
    ) -> None:
        content_hash = hashlib.md5(
            f"{post.title}{post.link}{post.summary}".encode()
        ).hexdigest()
        
        message = self._format_post_message(post)
        
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
    
    def _format_post_message(self, post: RSSPost) -> str:
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
        
        if post.summary:
            clean_summary = clean_html(post.summary)
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

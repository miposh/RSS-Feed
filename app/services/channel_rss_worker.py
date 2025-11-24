import logging
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import Dict, Deque, Optional

from aiogram import Bot
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.database.db import DB
from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.infrastructure.database.models.channel import ChannelModel
from app.services.fetcher.http_client import get_http_client
from app.services.parser.rss_parser import parse_rss_feed
from app.services.parser.models import RSSPost
from app.services.parser.article_extractor import extract_article_content

logger = logging.getLogger(__name__)


class ChannelRSSWorker:
    """Worker for a single channel's RSS feed processing."""
    
    def __init__(
        self,
        channel: ChannelModel,
        bot: Bot,
        db_pool: AsyncConnectionPool,
    ):
        self.channel = channel
        self.bot = bot
        self.db_pool = db_pool
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Rate limiting for Telegram
        self.message_timestamps: Deque[datetime] = deque()
        self.max_messages_per_minute = 20
        
        logger.info(
            f"Worker initialized for channel {self.channel.channel_id} ({self.channel.title}): "
            f"interval={self.channel.interval_time}s, scraper={self.channel.scraper_is_enabled}"
        )
    
    async def start(self) -> None:
        """Start the worker."""
        if self.running:
            logger.warning(f"Worker for channel {self.channel.channel_id} is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._check_feeds_loop())
        logger.info(
            f"Worker started for channel {self.channel.channel_id} ({self.channel.title}) "
            f"with interval {self.channel.interval_time}s"
        )
    
    async def stop(self) -> None:
        """Stop the worker."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Worker stopped for channel {self.channel.channel_id} ({self.channel.title})")
    
    async def update_settings(self, channel: ChannelModel) -> None:
        """Update worker settings and restart if necessary."""
        old_interval = self.channel.interval_time
        old_scraper = self.channel.scraper_is_enabled
        old_api_key = self.channel.scraper_api_key
        
        self.channel = channel
        
        # Check if settings changed
        settings_changed = (
            old_interval != channel.interval_time or
            old_scraper != channel.scraper_is_enabled or
            old_api_key != channel.scraper_api_key
        )
        
        if settings_changed:
            logger.info(
                f"Settings changed for channel {self.channel.channel_id}: "
                f"interval={old_interval}s→{channel.interval_time}s, "
                f"scraper={old_scraper}→{channel.scraper_is_enabled}, "
                f"api_key_changed={old_api_key != channel.scraper_api_key}"
            )
            
            # Restart the worker with new settings
            await self.stop()
            await self.start()
    
    async def _check_feeds_loop(self) -> None:
        """Main loop that checks feeds at the configured interval."""
        while self.running:
            try:
                await self._check_channel_feeds()
            except Exception as e:
                logger.error(
                    f"Error checking feeds for channel {self.channel.channel_id}: {e}",
                    exc_info=True
                )
            
            # Wait for the configured interval
            await asyncio.sleep(self.channel.interval_time)
    
    async def _check_channel_feeds(self) -> None:
        """Check all RSS feeds subscribed by this channel."""
        to_process = []

        async with self.db_pool.connection() as raw_connection:
            async with raw_connection.transaction():
                connection = PsycopgConnection(raw_connection)
                db = DB(connection)
                
                # Get all feed subscriptions for this channel
                subscriptions = await db.feed_subscriptions.get_subscriptions_by_channel(
                    channel_id=self.channel.id
                )
                
                if not subscriptions:
                    logger.debug(f"No subscriptions for channel {self.channel.channel_id}")
                    return
                
                for subscription in subscriptions:
                    # Get feed info
                    feed = await db.rss_feeds.get_feed(feed_id=subscription.feed_id)
                    if not feed or not feed.enabled:
                        continue
                    
                    to_process.append((subscription, feed))

        if not to_process:
            logger.debug(f"No enabled feeds for channel {self.channel.channel_id}")
            return

        logger.info(
            f"Checking {len(to_process)} feeds for channel {self.channel.channel_id} ({self.channel.title})"
        )
        
        # Process feeds concurrently with a limit
        semaphore = asyncio.Semaphore(5)  # Process max 5 feeds at once per channel

        async def process_with_semaphore(sub, fd):
            async with semaphore:
                try:
                    await self._process_feed(
                        feed_id=fd.id,
                        feed_url=fd.url,
                        last_modified=fd.last_modified,
                        etag=fd.etag,
                    )
                except Exception as e:
                     logger.error(
                        f"Error processing subscription {sub.id} for channel {self.channel.channel_id}: {e}",
                        exc_info=True
                    )

        await asyncio.gather(*(process_with_semaphore(sub, feed) for sub, feed in to_process))
    
    async def _process_feed(
        self,
        feed_id: int,
        feed_url: str,
        last_modified: str = None,
        etag: str = None
    ) -> None:
        """Process a single RSS feed."""
        logger.debug(f"Processing feed {feed_url} for channel {self.channel.channel_id}")
        
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
                
                async with self.db_pool.connection() as raw_connection:
                    async with raw_connection.transaction():
                        connection = PsycopgConnection(raw_connection)
                        db = DB(connection)
                        await db.rss_feeds.update_error_count(feed_id=feed_id)
                return
            
            posts = await parse_rss_feed(content_bytes)
            if not posts:
                logger.debug(f"No posts in feed {feed_url}")
                return
            
            # Identify new posts and filter out already sent ones
            new_posts = []
            
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    connection = PsycopgConnection(raw_connection)
                    db = DB(connection)
                    
                    for post in posts:
                        existing_post = await db.rss_posts.get_post_by_guid(
                            feed_id=feed_id,
                            guid=post.guid,
                        )
                        
                        if existing_post and existing_post.is_sent:
                            continue
                        
                        new_posts.append(post)
            
            if not new_posts:
                logger.debug(f"No new posts for channel {self.channel.channel_id}")
                return

            # Sort by published time (newest first)
            new_posts.sort(
                key=lambda p: p.published_time or datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            
            # Take top 3 to send, mark the rest as read
            posts_to_send = new_posts[:3]
            posts_to_mark = new_posts[3:]
            
            if posts_to_mark:
                logger.info(f"Marking {len(posts_to_mark)} old posts as read (limit 3)")
                for post in posts_to_mark:
                    await self._save_and_mark_post(feed_id=feed_id, post=post)
            
            # Process posts to send (oldest first to maintain chronological order in chat)
            for post in reversed(posts_to_send):
                await self._process_post(post, feed_id)
                
                # Add random delay between posts (10-15 seconds)
                delay = random.uniform(10, 15)
                logger.debug(f"Waiting {delay:.1f} seconds before next post...")
                await asyncio.sleep(delay)
            
            # Update feed metadata and reset error count on success
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    connection = PsycopgConnection(raw_connection)
                    db = DB(connection)
                    await db.rss_feeds.update_fetch_status(
                        feed_id=feed_id,
                        last_status=status,
                        etag=None,
                        last_modified=None,
                    )
                    await db.rss_feeds.reset_error_count(feed_id=feed_id)
            
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}", exc_info=True)
    
    async def _process_post(
        self,
        post: RSSPost,
        feed_id: int,
    ) -> None:
        """Process and send a single post to the channel."""
        # Extract full article content if scraper is enabled for this channel
        scraper_enabled = self.channel.scraper_is_enabled
        scraper_api_key = self.channel.scraper_api_key
        
        if scraper_enabled and scraper_api_key and post.link:
            try:
                logger.debug(f"Extracting full article text: {post.link}")
                full_article_text, article_images = await extract_article_content(
                    post.link,
                    api_key=scraper_api_key
                )
                
                if full_article_text:
                    # Replace content with full article text
                    post.content = full_article_text
                    logger.info(f"Successfully extracted full text ({len(full_article_text)} chars)")
                else:
                    logger.warning("Failed to extract full text, using RSS content")
                
                # Use only the extracted top_image if available
                if article_images:
                    post.image_urls = [article_images[0]]
                    logger.info("Using top_image from article")
                else:
                    post.image_urls = []

            except Exception as e:
                logger.error(f"Error extracting article: {e}", exc_info=True)

        # Prepare message
        message = await self._format_post_message(post, include_hidden_link=(len(post.image_urls) == 1))
        
        if not self._can_send_message():
            logger.warning(f"Rate limit exceeded for channel {self.channel.channel_id}")
            await asyncio.sleep(60)  # Wait a minute before retrying
        
        try:
            # Send as Album if multiple images
            if len(post.image_urls) > 1:
                # Telegram allows max 10 items in media group
                media_group = []
                for i, url in enumerate(post.image_urls[:10]):
                    media = InputMediaPhoto(media=url)
                    # Add caption to the first item if it fits
                    if i == 0 and len(message) <= 1024:
                        media.caption = message
                        media.parse_mode = "HTML"
                    media_group.append(media)
                
                # If message was too long for caption, send it separately first
                if len(message) > 1024:
                    await self.bot.send_message(
                        chat_id=self.channel.channel_id,
                        text=message,
                        disable_web_page_preview=False
                    )
                    # Send album without caption
                    await self.bot.send_media_group(
                        chat_id=self.channel.channel_id,
                        media=media_group
                    )
                else:
                    # Send album with caption
                    await self.bot.send_media_group(
                        chat_id=self.channel.channel_id,
                        media=media_group
                    )
            else:
                # Send as normal message (hidden link will handle the single image)
                await self.bot.send_message(
                    chat_id=self.channel.channel_id,
                    text=message,
                    disable_web_page_preview=False
                )
            
            self._track_sent_message()
            logger.info(
                f"Sent post to channel {self.channel.channel_id} ({self.channel.title}): {post.title[:50]}"
            )
            
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                logger.warning(
                    f"Channel {self.channel.channel_id} not found. Consider disabling parsing."
                )
            else:
                logger.error(f"Bad request for channel {self.channel.channel_id}: {e}")
        
        except TelegramForbiddenError:
            logger.warning(f"Bot forbidden in channel {self.channel.channel_id}")
        
        except Exception as e:
            logger.error(f"Error sending to channel {self.channel.channel_id} ({self.channel.title}): {e}")
            return
        
        self._track_sent_message()
        
        # Mark post as sent in database
        await self._save_and_mark_post(feed_id=feed_id, post=post)
    
    async def _save_and_mark_post(
        self,
        feed_id: int,
        post: RSSPost
    ) -> None:
        """Save post to database and mark it as sent."""
        try:
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    connection = PsycopgConnection(raw_connection)
                    db = DB(connection)
                    
                    # Add post to database
                    post_model = await db.rss_posts.add(
                        feed_id=feed_id,
                        guid=post.guid,
                        link=post.link,
                        title=post.title,
                        summary=post.summary,
                        content_html=post.content,
                        author=post.author,
                        published_at=post.published_time,
                        media_urls={"images": post.image_urls} if post.image_urls else None,
                    )
                    
                    if not post_model:
                        # Post already exists, get it
                        post_model = await db.rss_posts.get_post_by_guid(
                            feed_id=feed_id,
                            guid=post.guid
                        )
                    
                    if post_model:
                        await db.rss_posts.mark_as_sent(post_id=post_model.id)
                        logger.debug(f"Marked post as sent: {post.title[:50]}")
                    else:
                        logger.error(f"Failed to save/retrieve post: {post.guid}")
                        
        except Exception as e:
            logger.error(f"Error saving post {post.guid}: {e}", exc_info=True)
    
    async def _format_post_message(self, post: RSSPost, include_hidden_link: bool = False) -> str:
        """Format post message for Telegram."""
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
        
        message = ""
        
        # Add hidden link for image preview if available and requested
        if include_hidden_link and post.image_urls:
            message += f"<a href='{post.image_urls[0]}'>&#8203;</a>"
        
        message += f"<b>{clean_html(post.title)}</b>\n\n"
        
        # Use content if available, otherwise fall back to summary
        text_to_use = post.content if post.content else post.summary
        
        if text_to_use:
            clean_text = clean_html(text_to_use)
            
            # Limit to 4080 characters
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
    
    def _can_send_message(self) -> bool:
        """Check if we can send a message (rate limiting)."""
        now = datetime.now()
        
        # Remove timestamps older than 1 minute
        while self.message_timestamps and (now - self.message_timestamps[0]) > timedelta(minutes=1):
            self.message_timestamps.popleft()
        
        return len(self.message_timestamps) < self.max_messages_per_minute
    
    def _track_sent_message(self) -> None:
        """Track that a message was sent (for rate limiting)."""
        self.message_timestamps.append(datetime.now())


class ChannelRSSWorkerService:
    """Service that manages RSS workers for all enabled channels."""
    
    def __init__(self, bot: Bot, db_pool: AsyncConnectionPool):
        self.bot = bot
        self.db_pool = db_pool
        self.workers: Dict[int, ChannelRSSWorker] = {}  # channel_id -> worker
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_interval = 60  # Check for changes every 60 seconds
    
    async def start(self) -> None:
        """Start the worker service."""
        if self.running:
            logger.warning("ChannelRSSWorkerService is already running")
            return
        
        self.running = True
        
        # Initialize workers for all enabled channels
        await self._sync_workers()
        
        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_channels())
        
        logger.info(f"ChannelRSSWorkerService started with {len(self.workers)} active workers")
    
    async def stop(self) -> None:
        """Stop the worker service."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop monitoring task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all workers
        await self._stop_all_workers()
        
        logger.info("ChannelRSSWorkerService stopped")
    
    async def _monitor_channels(self) -> None:
        """Monitor channels and sync workers periodically."""
        while self.running:
            try:
                await asyncio.sleep(self.monitor_interval)
                await self._sync_workers()
            except Exception as e:
                logger.error(f"Error monitoring channels: {e}", exc_info=True)
    
    async def _sync_workers(self) -> None:
        """Synchronize workers with enabled channels."""
        try:
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    connection = PsycopgConnection(raw_connection)
                    db = DB(connection)
                    
                    # Get all channels with parsing enabled
                    enabled_channels = await db.channels.get_channels_with_parsing_enabled()
                    
                    if not enabled_channels:
                        enabled_channels = []
                    
                    enabled_channel_ids = {channel.channel_id for channel in enabled_channels}
                    current_worker_ids = set(self.workers.keys())
                    
                    # Start workers for new channels
                    for channel in enabled_channels:
                        if channel.channel_id not in current_worker_ids:
                            # New channel - create and start worker
                            worker = ChannelRSSWorker(channel, self.bot, self.db_pool)
                            await worker.start()
                            self.workers[channel.channel_id] = worker
                            logger.info(f"Started new worker for channel {channel.channel_id} ({channel.title})")
                        else:
                            # Existing channel - update settings
                            worker = self.workers[channel.channel_id]
                            await worker.update_settings(channel)
                    
                    # Stop workers for disabled channels
                    for channel_id in current_worker_ids - enabled_channel_ids:
                        worker = self.workers.pop(channel_id)
                        await worker.stop()
                        logger.info(f"Stopped worker for disabled channel {channel_id}")
        
        except Exception as e:
            logger.error(f"Error syncing workers: {e}", exc_info=True)
    
    async def _stop_all_workers(self) -> None:
        """Stop all active workers."""
        for worker in self.workers.values():
            await worker.stop()
        self.workers.clear()
    
    async def reload_channel(self, channel_id: int) -> None:
        """Reload a specific channel's worker (useful after settings change)."""
        try:
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    connection = PsycopgConnection(raw_connection)
                    db = DB(connection)
                    
                    channel = await db.channels.get_channel(channel_id=channel_id)
                    
                    if not channel:
                        logger.warning(f"Channel {channel_id} not found")
                        return
                    
                    if channel.parsing_is_enabled:
                        # Channel should be running
                        if channel_id in self.workers:
                            # Update existing worker
                            await self.workers[channel_id].update_settings(channel)
                        else:
                            # Start new worker
                            worker = ChannelRSSWorker(channel, self.bot, self.db_pool)
                            await worker.start()
                            self.workers[channel_id] = worker
                    else:
                        # Channel should not be running
                        if channel_id in self.workers:
                            worker = self.workers.pop(channel_id)
                            await worker.stop()
        
        except Exception as e:
            logger.error(f"Error reloading channel {channel_id}: {e}", exc_info=True)

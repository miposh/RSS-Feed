import html
import logging
import asyncio
import re
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from typing import Dict, Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.database.db import DB
from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.infrastructure.database.models.channel import ChannelModel
from app.services.fetcher.http_client import get_http_client
from app.services.parser.rss_parser import parse_rss_feed
from app.services.parser.models import RSSPost
from app.services.parser.article_extractor import extract_article_content
from app.services.message_queue import get_message_queue

logger = logging.getLogger(__name__)

# Max posts published per feed per check; the rest are marked read to avoid flooding.
MAX_POSTS_PER_CHECK = 3

# Max feeds fetched concurrently within a single channel.
MAX_CONCURRENT_FEEDS = 5

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MESSAGE_LIMIT = 4080

# Backoff after a failed feed check, so a persistently broken channel
# (bad interval_time, DB down) retries instead of spinning or dying.
DEFAULT_ERROR_BACKOFF_SECONDS = 60

# Placeholder bodies that carry no information and should be dropped.
USELESS_CONTENT_REGEX = re.compile(
    r"^\s*(none|null|\[mehr\]|\[more\]|read more|weiterlesen|lire la suite"
    r"|continuer la lecture|…|\.\.\.)\s*$",
    re.IGNORECASE,
)
MIN_CONTENT_LENGTH = 30

HTML_TAG_REGEX = re.compile(r"<[^>]+>")
WHITESPACE_REGEX = re.compile(r"\s+")


def _clean_html(text: str) -> str:
    """Strip HTML tags, decode entities and collapse whitespace."""
    if not text:
        return ""

    text = html.unescape(text)
    text = HTML_TAG_REGEX.sub("", text)
    return WHITESPACE_REGEX.sub(" ", text).strip()


def _is_useless_content(text: str) -> bool:
    """Check whether the body is a placeholder rather than real content."""
    if not text:
        return True

    cleaned = _clean_html(text)
    return len(cleaned) < MIN_CONTENT_LENGTH or bool(USELESS_CONTENT_REGEX.match(cleaned))


def format_post_message(post: RSSPost) -> str:
    """Render a post as a Telegram HTML message."""
    title = html.escape(_clean_html(post.title))
    message = f"<b>{title}</b>\n\n"

    text_to_use = post.content or post.summary

    if text_to_use and not _is_useless_content(text_to_use):
        clean_text = html.escape(_clean_html(text_to_use))

        # Reserve room for the title, the link and the timestamp. Clamp at 0:
        # a huge title would otherwise make this negative and clean_text[:-N]
        # would keep almost the whole body instead of truncating it.
        max_content_length = max(0, TELEGRAM_MESSAGE_LIMIT - len(message) - 150)

        if len(clean_text) > max_content_length:
            clean_text = clean_text[:max(0, max_content_length - 3)] + "..."

        message += f"{clean_text}\n\n"

    if post.link:
        # Escaped: feed URLs routinely carry & in query strings, which would
        # otherwise make Telegram reject the whole message as unparseable HTML.
        message += f'<a href="{html.escape(post.link, quote=True)}">Читать полностью</a>\n\n'

    if post.published_time:
        message += f"<i>📅 {post.published_time.strftime('%Y-%m-%d %H:%M')}</i>"

    return message


def _parse_http_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an HTTP date header into an aware UTC datetime.

    Headers with an unknown zone (``-0000``) parse as naive, so they are pinned
    to UTC rather than left for the database to interpret.
    """
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        logger.debug(f"Unparseable Last-Modified header: {value!r}")
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _format_http_date(value: Optional[datetime]) -> Optional[str]:
    """Render a stored timestamp as an ``If-Modified-Since`` header value.

    ``usegmt`` insists on ``timezone.utc`` specifically, and psycopg hands back
    ``ZoneInfo('Etc/UTC')``, so the value is converted first.
    """
    if not value:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return format_datetime(value.astimezone(timezone.utc), usegmt=True)


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

        # Get global message queue
        self.message_queue = get_message_queue()

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
        old_scraper_type = self.channel.scraper_type
        old_api_key = self.channel.scraper_api_key

        self.channel = channel

        settings_changed = (
            old_interval != channel.interval_time or
            old_scraper != channel.scraper_is_enabled or
            old_scraper_type != channel.scraper_type or
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
                # Sleep inside the try: a bad interval_time (None / non-numeric
                # column) would otherwise kill the loop while self.running stays
                # True, so the channel goes silent with nothing to restart it.
                await asyncio.sleep(self.channel.interval_time)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(
                    f"Error checking feeds for channel {self.channel.channel_id}: {e}",
                    exc_info=True
                )
                await asyncio.sleep(DEFAULT_ERROR_BACKOFF_SECONDS)

    async def _check_channel_feeds(self) -> None:
        """Check all enabled RSS feeds subscribed by this channel."""
        async with self.db_pool.connection() as raw_connection:
            db = DB(PsycopgConnection(raw_connection))
            feeds = await db.rss_feeds.get_feeds_by_channel(
                channel_id=self.channel.id,
                enabled_only=True,
            )

        if not feeds:
            logger.debug(f"No enabled feeds for channel {self.channel.channel_id}")
            return

        logger.info(
            f"Checking {len(feeds)} feeds for channel {self.channel.channel_id} ({self.channel.title})"
        )

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_FEEDS)

        async def process_with_semaphore(feed):
            async with semaphore:
                try:
                    await self._process_feed(feed)
                except Exception as e:
                    logger.error(
                        f"Error processing feed {feed.url} for channel {self.channel.channel_id}: {e}",
                        exc_info=True
                    )

        await asyncio.gather(*(process_with_semaphore(feed) for feed in feeds))

    async def _process_feed(self, feed) -> None:
        """Process a single RSS feed."""
        feed_id = feed.id
        feed_url = feed.url
        logger.debug(f"Processing feed {feed_url} for channel {self.channel.channel_id}")

        try:
            http_client = await get_http_client()
            result = await http_client.fetch(
                feed_url,
                etag=feed.etag,
                last_modified=_format_http_date(feed.last_modified),
            )

            if result.not_modified:
                logger.debug(f"Feed not modified: {feed_url}")
                return

            if not result.ok:
                logger.warning(f"Failed to fetch feed {feed_url}: {result.error}")

                async with self.db_pool.connection() as raw_connection:
                    async with raw_connection.transaction():
                        db = DB(PsycopgConnection(raw_connection))
                        await db.rss_feeds.update_error_count(feed_id=feed_id)
                return

            posts = await parse_rss_feed(result.content)
            if not posts:
                logger.debug(f"No posts in feed {feed_url}")
                return

            # Batch-check which posts were already delivered
            async with self.db_pool.connection() as raw_connection:
                db = DB(PsycopgConnection(raw_connection))
                sent_guids = await db.rss_posts.get_sent_guids(
                    feed_id=feed_id,
                    guids=[post.guid for post in posts],
                )

            new_posts = [post for post in posts if post.guid not in sent_guids]

            if not new_posts:
                logger.debug(f"No new posts for channel {self.channel.channel_id}")
                return

            # Sort by published time (newest first)
            new_posts.sort(
                key=lambda p: p.published_time or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )

            posts_to_send = new_posts[:MAX_POSTS_PER_CHECK]
            posts_to_mark = new_posts[MAX_POSTS_PER_CHECK:]

            if posts_to_mark:
                logger.info(f"Marking {len(posts_to_mark)} old posts as read (limit {MAX_POSTS_PER_CHECK})")
                for post in posts_to_mark:
                    await self._mark_post_sent(feed_id=feed_id, post=post)

            # Process posts to send (oldest first to maintain chronological order in chat)
            for post in reversed(posts_to_send):
                await self._process_post(post, feed_id)

            # Store cache validators so the next check can be a conditional request
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    db = DB(PsycopgConnection(raw_connection))
                    await db.rss_feeds.update_fetch_status(
                        feed_id=feed_id,
                        last_status=result.status,
                        etag=result.etag,
                        last_modified=_parse_http_date(result.last_modified),
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
        if self.channel.scraper_is_enabled and post.link:
            await self._enrich_with_article(post)

        image_url = post.image_urls[0] if post.image_urls else None
        message = format_post_message(post)

        # Pre-download the image so Telegram gets it from us with a browser
        # User-Agent, instead of fetching the URL itself and hitting a 403.
        image_data = None
        if image_url:
            try:
                http_client = await get_http_client()
                result = await http_client.fetch(image_url)
                if result.ok:
                    filename = image_url.split('/')[-1].split('?')[0] or 'image.jpg'
                    image_data = BufferedInputFile(result.content, filename=filename)
                else:
                    logger.warning(
                        f"Failed to download image {image_url}: {result.error or f'HTTP {result.status}'}"
                    )
            except Exception as e:
                logger.warning(f"Error downloading image {image_url}: {e}")

        async def send_message():
            try:
                if image_data:
                    await self.bot.send_photo(
                        chat_id=self.channel.channel_id,
                        photo=image_data,
                        caption=message[:TELEGRAM_CAPTION_LIMIT],
                        parse_mode="HTML",
                        show_caption_above_media=False
                    )
                else:
                    await self.bot.send_message(
                        chat_id=self.channel.channel_id,
                        text=message,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )

                # Marked only after Telegram accepted it. Marking at enqueue time
                # would drop the post permanently on any send failure, since
                # get_sent_guids would filter it out on the next pass.
                await self._mark_post_sent(feed_id=feed_id, post=post)

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
                raise

            except TelegramForbiddenError:
                logger.warning(f"Bot forbidden in channel {self.channel.channel_id}")
                raise

            except Exception as e:
                logger.error(f"Error sending to channel {self.channel.channel_id} ({self.channel.title}): {e}")
                raise

        # Enqueue the message (queue will handle rate limiting and flood control)
        await self.message_queue.enqueue(
            chat_id=self.channel.channel_id,
            send_func=send_message,
            priority=0
        )

        logger.debug(f"Enqueued post for channel {self.channel.channel_id}: {post.title[:50]}")

    async def _enrich_with_article(self, post: RSSPost) -> None:
        """Replace RSS excerpt with the full article text, when the scraper can get it."""
        try:
            logger.debug(f"Extracting full article text: {post.link}")
            full_article_text, article_images = await extract_article_content(
                post.link,
                scraper_type=self.channel.scraper_type,
                api_key=self.channel.scraper_api_key
            )

            if full_article_text:
                post.content = full_article_text
                logger.info(f"Successfully extracted full text ({len(full_article_text)} chars)")
            else:
                logger.warning("Failed to extract full text, using RSS content")

            # Only the article's top image is trustworthy; drop RSS-provided ones.
            post.image_urls = [article_images[0]] if article_images else []

        except Exception as e:
            logger.error(f"Error extracting article: {e}", exc_info=True)

    async def _mark_post_sent(
        self,
        feed_id: int,
        post: RSSPost
    ) -> None:
        """Persist the post and flag it as delivered."""
        try:
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    db = DB(PsycopgConnection(raw_connection))

                    saved = await db.rss_posts.add_sent(
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

                    if saved:
                        logger.debug(f"Marked post as sent: {post.title[:50]}")
                    else:
                        logger.error(f"Failed to save post: {post.guid}")

        except Exception as e:
            logger.error(f"Error saving post {post.guid}: {e}", exc_info=True)


class ChannelRSSWorkerService:
    """Service that manages RSS workers for all enabled channels."""

    def __init__(self, bot: Bot, db_pool: AsyncConnectionPool):
        self.bot = bot
        self.db_pool = db_pool
        self.workers: Dict[int, ChannelRSSWorker] = {}  # channel_id -> worker
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_interval = 60  # Check for changes every 60 seconds
        # Serialises sync_workers/reload_channel: both await a DB round-trip
        # before checking self.workers, so without it two callers can each see
        # "no worker" and start a duplicate that nothing ever stops.
        self._workers_lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the worker service."""
        if self.running:
            logger.warning("ChannelRSSWorkerService is already running")
            return

        self.running = True

        # Initialize workers for all enabled channels
        await self.sync_workers()

        # Start monitoring task
        self.monitor_task = asyncio.create_task(self._monitor_channels())

        logger.info(f"ChannelRSSWorkerService started with {len(self.workers)} active workers")

    async def stop(self) -> None:
        """Stop the worker service."""
        if not self.running:
            return

        self.running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        await self._stop_all_workers()

        logger.info("ChannelRSSWorkerService stopped")

    async def _monitor_channels(self) -> None:
        """Monitor channels and sync workers periodically."""
        while self.running:
            try:
                await asyncio.sleep(self.monitor_interval)
                await self.sync_workers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring channels: {e}", exc_info=True)

    async def sync_workers(self) -> None:
        """Synchronize workers with enabled channels."""
        try:
            async with self._workers_lock:
                async with self.db_pool.connection() as raw_connection:
                    db = DB(PsycopgConnection(raw_connection))
                    enabled_channels = await db.channels.get_channels_with_parsing_enabled() or []

                enabled_channel_ids = {channel.channel_id for channel in enabled_channels}
                current_worker_ids = set(self.workers.keys())

                for channel in enabled_channels:
                    worker = self.workers.get(channel.channel_id)
                    if worker is None:
                        worker = ChannelRSSWorker(channel, self.bot, self.db_pool)
                        await worker.start()
                        self.workers[channel.channel_id] = worker
                        logger.info(f"Started new worker for channel {channel.channel_id} ({channel.title})")
                    else:
                        await worker.update_settings(channel)

                for channel_id in current_worker_ids - enabled_channel_ids:
                    worker = self.workers.pop(channel_id)
                    await worker.stop()
                    logger.info(f"Stopped worker for disabled channel {channel_id}")

        except Exception as e:
            logger.error(f"Error syncing workers: {e}", exc_info=True)

    async def _stop_all_workers(self) -> None:
        """Stop all active workers."""
        await asyncio.gather(*(worker.stop() for worker in self.workers.values()))
        self.workers.clear()

    async def reload_channel(self, channel_id: int) -> None:
        """Reload a specific channel's worker (useful after settings change)."""
        try:
            async with self._workers_lock:
                async with self.db_pool.connection() as raw_connection:
                    db = DB(PsycopgConnection(raw_connection))
                    channel = await db.channels.get_channel(channel_id=channel_id)

                if not channel:
                    logger.warning(f"Channel {channel_id} not found")
                    return

                if channel.parsing_is_enabled:
                    worker = self.workers.get(channel_id)
                    if worker:
                        await worker.update_settings(channel)
                    else:
                        worker = ChannelRSSWorker(channel, self.bot, self.db_pool)
                        await worker.start()
                        self.workers[channel_id] = worker
                elif channel_id in self.workers:
                    worker = self.workers.pop(channel_id)
                    await worker.stop()

        except Exception as e:
            logger.error(f"Error reloading channel {channel_id}: {e}", exc_info=True)

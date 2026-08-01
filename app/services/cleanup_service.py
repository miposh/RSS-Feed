import logging
import asyncio
import gc

import psutil

from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.infrastructure.database.db import DB
from config.config import get_config

logger = logging.getLogger(__name__)

# Browser restart interval in seconds (1 hour)
BROWSER_RESTART_INTERVAL = 3600


class CleanupService:
    """Service for periodic cleanup of old data and memory management."""

    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.running = False
        self.task = None
        self.browser_task = None
        self.config = get_config()

    async def start(self):
        """Start the cleanup service."""
        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        self.browser_task = asyncio.create_task(self._browser_cleanup_loop())
        logger.info("CleanupService started (with browser memory cleanup)")

    async def stop(self):
        """Stop the cleanup service."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.browser_task:
            self.browser_task.cancel()
            try:
                await self.browser_task
            except asyncio.CancelledError:
                pass
        logger.info("CleanupService stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop."""
        while self.running:
            try:
                await self._cleanup_old_posts()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

            # Wait for the configured interval
            await asyncio.sleep(self.config.rss.cleanup_interval)

    async def _browser_cleanup_loop(self):
        """Periodic browser/memory cleanup to prevent memory leaks."""
        while self.running:
            try:
                await asyncio.sleep(BROWSER_RESTART_INTERVAL)
                await self._restart_browser()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in browser cleanup loop: {e}", exc_info=True)

    async def _restart_browser(self):
        """Restart botasaurus browser to free memory."""
        logger.info("Starting browser memory cleanup...")

        try:
            # Import here to avoid circular imports
            from app.services.scrapers.botasaurus.scraper import _get_fetch_html_func

            # Clear the lru_cache to force browser restart
            _get_fetch_html_func.cache_clear()
            logger.info("Cleared browser function cache")

            # Force garbage collection
            collected = gc.collect()
            logger.info(f"Garbage collected {collected} objects")

            mem_info = psutil.Process().memory_info()
            logger.info(
                f"Memory after cleanup: RSS={mem_info.rss / 1024 / 1024:.1f}MB, "
                f"VMS={mem_info.vms / 1024 / 1024:.1f}MB"
            )

        except Exception as e:
            logger.error(f"Failed to restart browser: {e}", exc_info=True)

    async def _cleanup_old_posts(self):
        """Delete old posts from database."""
        days = self.config.rss.sent_posts_retention_days
        logger.info(f"Starting cleanup of posts older than {days} days...")
        
        try:
            async with self.db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    connection = PsycopgConnection(raw_connection)
                    db = DB(connection)
                    
                    count = await db.rss_posts.delete_older_than(days=days)
                    logger.info(f"Cleanup completed. Removed {count} old posts.")

        except Exception as e:
            logger.error(f"Failed to cleanup old posts: {e}", exc_info=True)

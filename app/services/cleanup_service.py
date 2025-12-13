import logging
import asyncio

from psycopg import errors as pg_errors

from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.infrastructure.database.db import DB
from config.config import get_config

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for periodic cleanup of old data."""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.running = False
        self.task = None
        self.config = get_config()
        
    async def start(self):
        """Start the cleanup service."""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        logger.info("CleanupService started")

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
                    
        except pg_errors.UndefinedTable:
            logger.warning(
                "Table 'rss_posts' does not exist. "
                "Please run migrations: python apply_migrations.py"
            )
        except Exception as e:
            logger.error(f"Failed to cleanup old posts: {e}", exc_info=True)

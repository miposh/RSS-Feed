"""
Database schema management and migrations.

Manages SQL migration files execution and schema verification.
"""
import logging
from pathlib import Path

from app.infrastructure.database.connection.base import BaseConnection

logger = logging.getLogger(__name__)


class DatabaseSchema:
    SQL_DIR = Path(__file__).parent.parent.parent.parent / "migrations"
    
    # List of migration files to apply
    # Add new migrations here manually before running the bot
    MIGRATIONS_TO_APPLY = [
        # "001_create_users_table.sql",
        # "002_create_channels_table.sql",
        # "003_create_rss_feeds_table.sql",
        # "004_create_feed_subscriptions_table.sql",
        # "005_create_rss_posts_table.sql",
    ]
    
    def __init__(self, connection: BaseConnection):
        self.connection = connection
    
    async def create_tables(self) -> None:
        logger.info("Starting database schema initialization...")
        
        for sql_file in self.MIGRATIONS_TO_APPLY:
            file_path = self.SQL_DIR / sql_file
            
            if not file_path.exists():
                logger.warning(f"SQL file not found: {file_path}")
                continue
            
            try:
                sql_content = file_path.read_text(encoding="utf-8")
                await self.connection.execute(sql=sql_content)
                
                logger.info(f"✓ Executed: {sql_file}")
                
            except Exception as e:
                logger.error(f"✗ Failed to execute {sql_file}: {e}")
                raise
        
        logger.info("Database schema initialization completed successfully!")
    
    async def apply_migrations(self) -> None:
        """Apply migrations listed in MIGRATIONS_TO_APPLY."""
        if not self.MIGRATIONS_TO_APPLY:
            logger.info("No migrations to apply")
            return
        
        logger.info(f"Applying {len(self.MIGRATIONS_TO_APPLY)} migration(s)...")
        
        for sql_file in self.MIGRATIONS_TO_APPLY:
            file_path = self.SQL_DIR / sql_file
            
            if not file_path.exists():
                logger.error(f"Migration file not found: {file_path}")
                raise FileNotFoundError(f"Migration file not found: {file_path}")
            
            try:
                sql_content = file_path.read_text(encoding="utf-8")
                await self.connection.execute(sql=sql_content)
                
                logger.info(f"✓ Applied: {sql_file}")
                
            except Exception as e:
                logger.error(f"✗ Failed to apply {sql_file}: {e}")
                raise
        
        logger.info("All migrations applied successfully!")
    
    async def verify_tables(self) -> bool:
        required_tables = [
            "users",
            "channels", 
            "rss_feeds",
            "feed_subscriptions",
            "rss_posts"
        ]
        
        try:
            result = await self.connection.fetchone(
                sql="""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = ANY(%s)
                """,
                params=(required_tables,)
            )
            
            count = result.data.get("count", 0) if result.data else 0
            
            if count == len(required_tables):
                logger.info(f"✓ All {count} required tables exist")
                return True
            else:
                logger.warning(f"⚠ Only {count}/{len(required_tables)} tables exist")
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify tables: {e}")
            return False
    
    async def drop_all_tables(self) -> None:
        logger.warning("⚠️  Dropping all tables...")
        
        try:
            await self.connection.execute(
                sql="""
                    DROP TABLE IF EXISTS rss_posts CASCADE;
                    DROP TABLE IF EXISTS feed_subscriptions CASCADE;
                    DROP TABLE IF EXISTS rss_feeds CASCADE;
                    DROP TABLE IF EXISTS channels CASCADE;
                    DROP TABLE IF EXISTS users CASCADE;
                    DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
                """
            )
            logger.info("✓ All tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    async def get_table_info(self) -> dict:
        try:
            result = await self.connection.fetchmany(
                sql="""
                    SELECT 
                        table_name,
                        (xpath('/row/cnt/text()', 
                            query_to_xml(format('SELECT COUNT(*) as cnt FROM %I', table_name), 
                            false, true, '')))[1]::text::int as row_count
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """
            )
            
            tables = {}
            if result and not result.is_empty():
                for row in result.data:
                    tables[row['table_name']] = row.get('row_count', 0)
            
            return tables
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {}

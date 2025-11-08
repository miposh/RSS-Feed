import asyncio
import logging

from app.infrastructure.database.connection.connect_to_pg import get_pg_connection
from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.infrastructure.database.schema import DatabaseSchema
from config.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    config = get_config()
    
    logger.info("Connecting to database...")
    connection = await get_pg_connection(
        db_name=config.postgres.name,
        host=config.postgres.host,
        port=config.postgres.port,
        user=config.postgres.user,
        password=config.postgres.password,
    )
    
    try:
        wrapped_connection = PsycopgConnection(connection)
        schema = DatabaseSchema(wrapped_connection)
        
        await schema.apply_migrations()
        
        logger.info("✓ Migration process completed successfully!")
        logger.info("Don't forget to clear MIGRATIONS_TO_APPLY list in schema.py")
        
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        raise
    finally:
        await connection.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())

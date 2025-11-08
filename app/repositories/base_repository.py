import aiosqlite
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class BaseRepository:
    _connection_pool: Optional[aiosqlite.Connection] = None
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def get_connection(self) -> aiosqlite.Connection:
        if BaseRepository._connection_pool is None:
            try:
                BaseRepository._connection_pool = await aiosqlite.connect(self.db_path)
                # Enable foreign keys
                await BaseRepository._connection_pool.execute("PRAGMA foreign_keys = ON")
                logger.info(f"Created new database connection to {self.db_path}")
            except Exception as e:
                logger.error(f"Error connecting to database: {e}", exc_info=True)
                raise
                
        return BaseRepository._connection_pool
    
    @staticmethod
    async def close_connection() -> None:
        if BaseRepository._connection_pool is not None:
            await BaseRepository._connection_pool.close()
            BaseRepository._connection_pool = None
            logger.info("Database connection closed")
    
    async def execute(self, query: str, parameters: tuple = ()) -> Any:
        conn = await self.get_connection()
        try:
            return await conn.execute(query, parameters)
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            raise
    
    async def execute_and_commit(self, query: str, parameters: tuple = ()) -> Any:
        conn = await self.get_connection()
        try:
            result = await conn.execute(query, parameters)
            await conn.commit()
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            raise 
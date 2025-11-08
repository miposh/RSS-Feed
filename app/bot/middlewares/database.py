"""
Database middleware for aiogram.

Provides database connection and transaction management for each update.
"""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.database.db import DB
from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection

logger = logging.getLogger(__name__)


class DataBaseMiddleware(BaseMiddleware):
    """
    Middleware that provides database connection for each update.
    
    Wraps each update handler in a database transaction.
    If handler completes successfully, transaction is committed.
    If handler raises an exception, transaction is rolled back.
    
    Usage:
        dp.update.middleware(DataBaseMiddleware())
        dp.errors.middleware(DataBaseMiddleware())
    
    The middleware expects `db_pool` to be available in workflow_data:
        dp.workflow_data.update(db_pool=db_pool)
    
    Handlers can access the database via `data["db"]`:
        async def my_handler(message: Message, db: DB):
            user = await db.users.get_user(user_id=message.from_user.id)
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        """
        Process update with database connection.
        
        Args:
            handler: Next handler in the chain
            event: Telegram update event
            data: Handler data dictionary
            
        Returns:
            Handler result
            
        Raises:
            RuntimeError: If db_pool is not provided in middleware data
        """
        db_pool: AsyncConnectionPool = data.get("db_pool")

        if db_pool is None:
            logger.error("Database pool is not provided in middleware data.")
            raise RuntimeError("Missing db_pool in middleware context.")

        async with db_pool.connection() as raw_connection:
            try:
                async with raw_connection.transaction():
                    # Wrap raw connection in our abstraction
                    connection = PsycopgConnection(raw_connection)
                    
                    # Create DB instance with all tables
                    data["db"] = DB(connection)
                    
                    # Call next handler
                    return await handler(event, data)
                    
            except Exception as e:
                logger.exception("Transaction rolled back due to error: %s", e)
                raise

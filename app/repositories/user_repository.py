"""
User repository using psycopg with raw SQL queries.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from psycopg import AsyncConnection
from psycopg.rows import class_row


@dataclass
class User:
    """User data model."""
    id: int
    user_id: int
    username: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserRepository:
    """Repository for User operations."""
    
    def __init__(self, conn: AsyncConnection):
        self.conn = conn
    
    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """
        Get user by Telegram user_id.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User or None if not found
        """
        async with self.conn.cursor(row_factory=class_row(User)) as cur:
            await cur.execute(
                """
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )
            return await cur.fetchone()
    
    async def get_by_id(self, id: int) -> Optional[User]:
        """
        Get user by internal ID.
        
        Args:
            id: Internal database ID
            
        Returns:
            User or None if not found
        """
        async with self.conn.cursor(row_factory=class_row(User)) as cur:
            await cur.execute(
                """
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                WHERE id = %s
                """,
                (id,)
            )
            return await cur.fetchone()
    
    async def find_by_username(self, username: str) -> list[User]:
        """
        Find users by username (case-insensitive search).
        
        Args:
            username: Username to search for
            
        Returns:
            List of matching users
        """
        async with self.conn.cursor(row_factory=class_row(User)) as cur:
            await cur.execute(
                """
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                WHERE username ILIKE %s
                """,
                (f"%{username}%",)
            )
            return await cur.fetchall()
    
    async def upsert_from_bot(
        self, 
        user_id: int, 
        username: Optional[str] = None
    ) -> User:
        """
        Create or update user from Telegram data.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username (without @)
            
        Returns:
            User instance
        """
        async with self.conn.cursor(row_factory=class_row(User)) as cur:
            await cur.execute(
                """
                INSERT INTO users (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username
                RETURNING id, user_id, username, created_at, updated_at
                """,
                (user_id, username)
            )
            result = await cur.fetchone()
            if result is None:
                raise RuntimeError("Failed to upsert user")
            return result
    
    async def update_username(self, user_id: int, username: str) -> Optional[User]:
        """
        Update user's username.
        
        Args:
            user_id: Telegram user ID
            username: New username
            
        Returns:
            Updated User or None if not found
        """
        async with self.conn.cursor(row_factory=class_row(User)) as cur:
            await cur.execute(
                """
                UPDATE users
                SET username = %s
                WHERE user_id = %s
                RETURNING id, user_id, username, created_at, updated_at
                """,
                (username, user_id)
            )
            return await cur.fetchone()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """
        Get all users with pagination.
        
        Args:
            limit: Number of records
            offset: Offset
            
        Returns:
            List of users
        """
        async with self.conn.cursor(row_factory=class_row(User)) as cur:
            await cur.execute(
                """
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            return await cur.fetchall()
    
    async def exists(self, user_id: int) -> bool:
        """
        Check if user exists.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user exists
        """
        async with self.conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE user_id = %s",
                (user_id,)
            )
            return await cur.fetchone() is not None

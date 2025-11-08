import logging
from typing import Optional

from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class GroupRepository(BaseRepository):
    async def add_group(self, chat_id: int) -> bool:
        
        try:
            existing_id = await self.get_group_id(chat_id)
            if existing_id is not None:
                logger.info(f"Group {chat_id} already exists, skipping addition")
                return True
                
            await self.execute_and_commit(
                "INSERT INTO groups (chat_id) VALUES (?)",
                (chat_id,)
            )
            logger.info(f"Group {chat_id} added")
            return True
        except Exception as e:
            logger.info(f"Failed to add group {chat_id}: {e}")
            return False
    
    async def remove_group(self, chat_id: int) -> bool:
        try:
            await self.execute_and_commit(
                "DELETE FROM groups WHERE chat_id = ?",
                (chat_id,)
            )
            logger.info(f"Group {chat_id} removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove group {chat_id}: {e}")
            return False
    
    async def get_group_id(self, chat_id: int) -> Optional[int]:
        try:
            cursor = await self.execute(
                "SELECT id FROM groups WHERE chat_id = ?",
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get group ID for chat {chat_id}: {e}")
            return None 
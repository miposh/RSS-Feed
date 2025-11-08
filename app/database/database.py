import aiosqlite
import logging
import os
from pathlib import Path
from typing import List, Tuple

from config.config import config
from database.schema import CREATE_TABLES_SQL, CREATE_TRIGGERS_SQL, PRAGMA_SETTINGS

logger = logging.getLogger(__name__)

DB_PATH = config.db_path

async def init_db() -> None:
    db_path = Path(DB_PATH)
    db_dir = db_path.parent
    
    if not db_dir.exists():
        logger.info(f"Directory {db_dir} does not exist, creating...")
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory {db_dir} created successfully")
        except Exception as e:
            logger.error(f"Error creating directory {db_dir}: {e}", exc_info=True)
            raise
    
    try:
        if not os.access(db_dir, os.W_OK):
            logger.error(f"No write permission for directory {db_dir}")
            raise PermissionError(f"No write permission for directory {db_dir}")
        logger.info(f"Directory {db_dir} is writable")
    except Exception as e:
        logger.error(f"Error checking access permissions: {e}", exc_info=True)
        raise
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            for pragma in PRAGMA_SETTINGS.strip().split(';'):
                if pragma.strip():
                    await db.execute(pragma.strip())
            
            await db.executescript(CREATE_TABLES_SQL)
            
            await db.executescript(CREATE_TRIGGERS_SQL)
            
            await db.commit()
            logger.info("Database schema initialized successfully with new structure")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise

async def add_group(chat_id: int) -> bool:
    from app.repositories.group_repository import GroupRepository
    repo = GroupRepository(DB_PATH)
    return await repo.add_group(chat_id)

async def remove_group(chat_id: int) -> bool:
    from app.repositories.group_repository import GroupRepository
    repo = GroupRepository(DB_PATH)
    return await repo.remove_group(chat_id)

async def add_rss_feed(url: str, chat_id: int) -> bool:
    from app.repositories.group_repository import GroupRepository
    from app.repositories.rss_repository import RSSRepository
    
    group_repo = GroupRepository(DB_PATH)
    rss_repo = RSSRepository(DB_PATH)
    
    group_id = await group_repo.get_group_id(chat_id)
    if group_id is None:
        return False
    
    return await rss_repo.add_feed(url, group_id)

async def remove_rss_feed(url: str, chat_id: int) -> bool:
    from app.repositories.group_repository import GroupRepository
    from app.repositories.rss_repository import RSSRepository
    
    group_repo = GroupRepository(DB_PATH)
    rss_repo = RSSRepository(DB_PATH)
    
    group_id = await group_repo.get_group_id(chat_id)
    if group_id is None:
        return False
    
    return await rss_repo.remove_feed(url, group_id)

async def get_rss_feeds_for_group(chat_id: int) -> List[str]:
    from app.repositories.group_repository import GroupRepository
    from app.repositories.rss_repository import RSSRepository
    
    group_repo = GroupRepository(DB_PATH)
    rss_repo = RSSRepository(DB_PATH)
    
    group_id = await group_repo.get_group_id(chat_id)
    if group_id is None:
        return []
    
    return await rss_repo.get_feeds_for_group(group_id)

async def get_all_feeds() -> List[Tuple[int, str, int]]:
    from app.repositories.rss_repository import RSSRepository
    
    rss_repo = RSSRepository(DB_PATH)
    return await rss_repo.get_all_feeds()

async def is_post_sent(post_guid: str, feed_id: int) -> bool:
    from app.repositories.rss_repository import RSSRepository
    
    rss_repo = RSSRepository(DB_PATH)
    return await rss_repo.is_post_sent(post_guid, feed_id)

async def mark_post_as_sent(post_guid: str, feed_id: int) -> bool:
    from app.repositories.rss_repository import RSSRepository
    
    rss_repo = RSSRepository(DB_PATH)
    return await rss_repo.mark_post_as_sent(post_guid, feed_id)

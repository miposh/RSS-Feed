"""
Channel administrator synchronization.

Group admins are mirrored from the Telegram API into the ``channel_admins``
table so the bot can scope every dialog to the groups a user actually
administers.
"""
import asyncio
import logging

from aiogram import Bot
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.infrastructure.database.db import DB

logger = logging.getLogger(__name__)

SYNC_FAILED = -1

# Pause between Telegram API calls while backfilling, to stay well under rate limits.
BACKFILL_DELAY_SECONDS = 0.5


async def sync_group_admins(
    bot: Bot,
    db: DB,
    chat_id: int,
    internal_channel_id: int,
) -> int:
    """Sync group administrators from the Telegram API to the database.

    Returns the number of synced human admins, or ``SYNC_FAILED`` on API failure.
    """
    try:
        chat_admins = await bot.get_chat_administrators(chat_id)
    except Exception as e:
        logger.error(f"Failed to get administrators for chat {chat_id}: {e}")
        return SYNC_FAILED

    human_admins = [member for member in chat_admins if not member.user.is_bot]

    if not human_admins:
        logger.warning(f"No human admins found in chat {chat_id}, skipping sync")
        return SYNC_FAILED

    internal_user_ids = await db.users.add_many(
        users=[(member.user.id, member.user.username) for member in human_admins]
    )

    await db.channel_admins.sync_admins(
        internal_channel_id=internal_channel_id,
        admin_internal_user_ids=internal_user_ids,
    )

    logger.info(f"Synced {len(internal_user_ids)} admin(s) for chat {chat_id}")
    return len(internal_user_ids)


async def backfill_channel_admins(bot: Bot, db_pool: AsyncConnectionPool) -> int:
    """Populate admins for channels that have none recorded yet.

    Channels registered before admin tracking existed have no rows in
    ``channel_admins``, which would hide them from every dialog. Each channel is
    synced in its own transaction so one failure cannot roll back the rest.

    Returns:
        The number of channels successfully backfilled.
    """
    async with db_pool.connection() as raw_connection:
        db = DB(PsycopgConnection(raw_connection))
        channels = await db.channels.get_channels_without_admins()

    if not channels:
        logger.info("Channel admin backfill: nothing to do")
        return 0

    logger.info(f"Channel admin backfill: {len(channels)} channel(s) without admins")

    backfilled = 0
    for channel in channels:
        try:
            async with db_pool.connection() as raw_connection:
                async with raw_connection.transaction():
                    db = DB(PsycopgConnection(raw_connection))
                    synced = await sync_group_admins(
                        bot=bot,
                        db=db,
                        chat_id=channel.channel_id,
                        internal_channel_id=channel.id,
                    )

            if synced != SYNC_FAILED:
                backfilled += 1
        except Exception as e:
            logger.error(
                f"Channel admin backfill failed for {channel.channel_id} ({channel.title}): {e}",
                exc_info=True,
            )

        await asyncio.sleep(BACKFILL_DELAY_SECONDS)

    logger.info(f"Channel admin backfill completed: {backfilled}/{len(channels)} channel(s)")
    return backfilled

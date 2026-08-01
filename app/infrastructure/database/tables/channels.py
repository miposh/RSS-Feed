import logging
from typing import Optional

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.channel import ChannelModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.channels import ChannelsTableAction

logger = logging.getLogger(__name__)

# Explicit column list so SELECTs stay stable when new columns are added.
CHANNEL_COLUMNS = (
    "id, channel_id, username, title, parsing_is_enabled, "
    "interval_time, scraper_is_enabled, scraper_type, scraper_api_key, created_at"
)


class ChannelsTable(BaseTable):
    __tablename__ = "channels"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    async def add(
        self,
        *,
        channel_id: int,
        username: Optional[str] = None,
        title: str,
    ) -> ChannelModel | None:
        """Add a new channel."""
        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO channels(channel_id, username, title)
                VALUES(%s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE
                SET username = EXCLUDED.username, title = EXCLUDED.title
                RETURNING *;
            """,
            params=(channel_id, username, title),
        )
        channel_model = data.to_model(model=ChannelModel)
        self._log(
            ChannelsTableAction.ADD,
            channel_id=channel_id,
            username=username,
            title=title,
        )
        return channel_model

    async def delete(self, *, channel_id: int) -> None:
        """Delete a channel."""
        await self.connection.execute(
            sql="""
                DELETE FROM channels WHERE channel_id = %s;
            """,
            params=(channel_id,),
        )
        self._log(ChannelsTableAction.DELETE, channel_id=channel_id)

    async def get_channel(self, *, channel_id: int) -> ChannelModel | None:
        """Get channel by channel_id."""
        data: SingleQueryResult = await self.connection.fetchone(
            sql=f"""
                SELECT {CHANNEL_COLUMNS}
                FROM channels
                WHERE channel_id = %s
            """,
            params=(channel_id,),
        )
        channel_model = data.to_model(model=ChannelModel)
        self._log(ChannelsTableAction.GET_CHANNEL, channel_id=channel_id)
        return channel_model

    async def toggle_parsing(self, *, channel_id: int) -> ChannelModel | None:
        """Toggle RSS parsing for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET parsing_is_enabled = NOT parsing_is_enabled
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(channel_id,),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, parsing_is_enabled=channel_model.parsing_is_enabled)
        return channel_model

    async def update_interval_time(self, *, channel_id: int, interval_time: int) -> ChannelModel | None:
        """Update RSS check interval for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET interval_time = %s
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(interval_time, channel_id),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, interval_time=interval_time)
        return channel_model

    async def toggle_scraper(self, *, channel_id: int) -> ChannelModel | None:
        """Toggle scraper for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET scraper_is_enabled = NOT scraper_is_enabled
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(channel_id,),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, scraper_is_enabled=channel_model.scraper_is_enabled)
        return channel_model

    async def update_scraper_api_key(self, *, channel_id: int, api_key: Optional[str]) -> ChannelModel | None:
        """Update scraper API key for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET scraper_api_key = %s
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(api_key, channel_id),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, scraper_api_key_set=api_key is not None)
        return channel_model

    async def update_scraper_type(self, *, channel_id: int, scraper_type: str) -> ChannelModel | None:
        """Update scraper type for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET scraper_type = %s
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(scraper_type, channel_id),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, scraper_type=scraper_type)
        return channel_model

    async def get_channels_with_parsing_enabled(self) -> list[ChannelModel] | None:
        """Get all channels with parsing enabled."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql=f"""
                SELECT {CHANNEL_COLUMNS}
                FROM channels
                WHERE parsing_is_enabled = TRUE
                ORDER BY created_at DESC
            """,
        )
        channels = data.to_models(model=ChannelModel)
        self._log(ChannelsTableAction.GET_ALL_CHANNELS, count=len(data), parsing_enabled=True)
        return channels

    async def get_channels_for_admin(self, *, telegram_user_id: int) -> list[ChannelModel] | None:
        """Get all channels where a Telegram user is an admin."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql=f"""
                SELECT {CHANNEL_COLUMNS}
                FROM channels
                WHERE id IN (
                    SELECT ca.channel_id
                    FROM channel_admins ca
                    JOIN users u ON ca.user_id = u.id
                    WHERE u.user_id = %s
                )
                ORDER BY created_at DESC
            """,
            params=(telegram_user_id,),
        )
        channels = data.to_models(model=ChannelModel)
        self._log(ChannelsTableAction.GET_CHANNELS_FOR_ADMIN, telegram_user_id=telegram_user_id, count=len(data))
        return channels

    async def get_channels_without_admins(self) -> list[ChannelModel] | None:
        """Get channels that have no admins recorded yet (backfill candidates)."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql=f"""
                SELECT {CHANNEL_COLUMNS}
                FROM channels c
                WHERE NOT EXISTS (
                    SELECT 1 FROM channel_admins ca WHERE ca.channel_id = c.id
                )
                ORDER BY created_at DESC
            """,
        )
        channels = data.to_models(model=ChannelModel)
        self._log(ChannelsTableAction.GET_CHANNELS_WITHOUT_ADMINS, count=len(data))
        return channels

    async def set_parsing_for_admin(self, *, telegram_user_id: int, enabled: bool) -> int:
        """Enable or disable parsing for every channel a user administers.

        Returns:
            Number of channels whose state actually changed.
        """
        result = await self.connection.execute(
            sql="""
                UPDATE channels
                SET parsing_is_enabled = %s
                WHERE parsing_is_enabled <> %s
                AND id IN (
                    SELECT ca.channel_id
                    FROM channel_admins ca
                    JOIN users u ON ca.user_id = u.id
                    WHERE u.user_id = %s
                )
            """,
            params=(enabled, enabled, telegram_user_id),
        )
        self._log(
            ChannelsTableAction.UPDATE_CHANNEL,
            telegram_user_id=telegram_user_id,
            parsing_is_enabled=enabled,
            updated=result,
        )
        return max(result, 0)

    async def set_api_key_for_admin(self, *, telegram_user_id: int, api_key: Optional[str]) -> int:
        """Set the scraper API key for every channel a user administers.

        Returns:
            Number of updated channels.
        """
        result = await self.connection.execute(
            sql="""
                UPDATE channels
                SET scraper_api_key = %s
                WHERE id IN (
                    SELECT ca.channel_id
                    FROM channel_admins ca
                    JOIN users u ON ca.user_id = u.id
                    WHERE u.user_id = %s
                )
            """,
            params=(api_key, telegram_user_id),
        )
        self._log(
            ChannelsTableAction.UPDATE_CHANNEL,
            telegram_user_id=telegram_user_id,
            scraper_api_key_set=api_key is not None,
            updated=result,
        )
        return max(result, 0)

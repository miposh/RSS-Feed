import logging
from typing import Optional

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.channel import ChannelModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.channels import ChannelsTableAction

logger = logging.getLogger(__name__)


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
            sql="""
                SELECT id, channel_id, username, title, parsing_is_enabled, 
                       interval_time, scraper_is_enabled, scraper_api_key, created_at
                FROM channels
                WHERE channel_id = %s
            """,
            params=(channel_id,),
        )
        channel_model = data.to_model(model=ChannelModel)
        self._log(ChannelsTableAction.GET_CHANNEL, channel_id=channel_id)
        return channel_model

    async def get_channel_by_id(self, *, id: int) -> ChannelModel | None:
        """Get channel by internal id."""
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT id, channel_id, username, title, parsing_is_enabled, 
                       interval_time, scraper_is_enabled, scraper_api_key, created_at
                FROM channels
                WHERE id = %s
            """,
            params=(id,),
        )
        channel_model = data.to_model(model=ChannelModel)
        self._log(ChannelsTableAction.GET_CHANNEL_BY_ID, id=id)
        return channel_model

    async def update_channel(
        self, *, channel_id: int, username: Optional[str] = None, title: Optional[str] = None
    ) -> ChannelModel | None:
        """Update channel info."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET username = COALESCE(%s, username),
                    title = COALESCE(%s, title)
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(username, title, channel_id),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(
            ChannelsTableAction.UPDATE_CHANNEL,
            channel_id=channel_id,
            username=username,
            title=title,
        )
        return channel_model

    async def get_all_channels(self) -> list[ChannelModel] | None:
        """Get all channels."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT id, channel_id, username, title, parsing_is_enabled, 
                       interval_time, scraper_is_enabled, scraper_api_key, created_at
                FROM channels
                ORDER BY created_at DESC
            """,
        )
        channels = data.to_models(model=ChannelModel)
        self._log(ChannelsTableAction.GET_ALL_CHANNELS, count=len(data) if data else 0)
        return channels

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

    async def enable_parsing(self, *, channel_id: int) -> ChannelModel | None:
        """Enable RSS parsing for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET parsing_is_enabled = TRUE
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(channel_id,),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, parsing_is_enabled=True)
        return channel_model

    async def disable_parsing(self, *, channel_id: int) -> ChannelModel | None:
        """Disable RSS parsing for a channel."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE channels
                SET parsing_is_enabled = FALSE
                WHERE channel_id = %s
                RETURNING *;
            """,
            params=(channel_id,),
        )
        channel_model = data.to_model(model=ChannelModel, raise_if_empty=True)
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, parsing_is_enabled=False)
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
        self._log(ChannelsTableAction.UPDATE_CHANNEL, channel_id=channel_id, scraper_api_key=api_key)
        return channel_model

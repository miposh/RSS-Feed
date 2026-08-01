import logging

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.channel_admin import ChannelAdminModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.channel_admins import ChannelAdminsTableAction

logger = logging.getLogger(__name__)


class ChannelAdminsTable(BaseTable):
    __tablename__ = "channel_admins"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    async def add(
        self,
        *,
        channel_id: int,
        user_id: int,
    ) -> ChannelAdminModel | None:
        """Add a user as admin for a channel (by internal IDs). Upsert: updates synced_at on conflict."""
        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO channel_admins(channel_id, user_id, synced_at)
                VALUES(%s, %s, NOW())
                ON CONFLICT (channel_id, user_id) DO UPDATE
                SET synced_at = NOW()
                RETURNING *;
            """,
            params=(channel_id, user_id),
        )
        admin_model = data.to_model(model=ChannelAdminModel)
        self._log(ChannelAdminsTableAction.ADD, channel_id=channel_id, user_id=user_id)
        return admin_model

    async def is_admin(self, *, telegram_user_id: int, telegram_channel_id: int) -> bool:
        """Check if a Telegram user is admin for a Telegram channel.

        Resolves both Telegram IDs through JOINs with users and channels tables.
        """
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT ca.id
                FROM channel_admins ca
                JOIN users u ON ca.user_id = u.id
                JOIN channels c ON ca.channel_id = c.id
                WHERE u.user_id = %s AND c.channel_id = %s
            """,
            params=(telegram_user_id, telegram_channel_id),
        )
        is_admin = not data.is_empty()
        self._log(
            ChannelAdminsTableAction.IS_ADMIN,
            telegram_user_id=telegram_user_id,
            telegram_channel_id=telegram_channel_id,
            result=is_admin,
        )
        return is_admin

    async def sync_admins(
        self,
        *,
        internal_channel_id: int,
        admin_internal_user_ids: list[int],
    ) -> list[ChannelAdminModel]:
        """Replace the admin set of a channel with the given users.

        Upserts the new set and drops anyone no longer in it, in two statements
        regardless of how many admins the channel has. Existing rows keep their
        ``created_at``, so only ``synced_at`` moves for admins that stayed.

        Args:
            internal_channel_id: The channels.id (internal PK)
            admin_internal_user_ids: List of users.id (internal PKs) for the admins

        Returns:
            The channel's admin records after the sync
        """
        user_ids = list(dict.fromkeys(admin_internal_user_ids))

        if not user_ids:
            await self.connection.execute(
                sql="DELETE FROM channel_admins WHERE channel_id = %s;",
                params=(internal_channel_id,),
            )
            self._log(
                ChannelAdminsTableAction.SYNC_ADMINS,
                channel_id=internal_channel_id,
                admin_count=0,
            )
            return []

        await self.connection.execute(
            sql="""
                DELETE FROM channel_admins
                WHERE channel_id = %s AND user_id <> ALL(%s::bigint[]);
            """,
            params=(internal_channel_id, user_ids),
        )

        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                INSERT INTO channel_admins(channel_id, user_id, synced_at)
                SELECT %s, user_id, NOW()
                FROM UNNEST(%s::bigint[]) AS user_id
                ON CONFLICT (channel_id, user_id) DO UPDATE
                SET synced_at = NOW()
                RETURNING *;
            """,
            params=(internal_channel_id, user_ids),
        )

        admins = data.to_models(model=ChannelAdminModel) or []
        self._log(
            ChannelAdminsTableAction.SYNC_ADMINS,
            channel_id=internal_channel_id,
            admin_count=len(admins),
        )
        return admins

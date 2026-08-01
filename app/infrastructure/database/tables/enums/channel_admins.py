from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class ChannelAdminsTableAction(BaseTableActionEnum):
    ADD = "ADD"
    IS_ADMIN = "IS_ADMIN"
    SYNC_ADMINS = "SYNC_ADMINS"

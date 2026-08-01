from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class ChannelsTableAction(BaseTableActionEnum):
    ADD = "ADD"
    DELETE = "DELETE"
    GET_CHANNEL = "GET_CHANNEL"
    UPDATE_CHANNEL = "UPDATE_CHANNEL"
    GET_ALL_CHANNELS = "GET_ALL_CHANNELS"
    GET_CHANNELS_FOR_ADMIN = "GET_CHANNELS_FOR_ADMIN"
    GET_CHANNELS_WITHOUT_ADMINS = "GET_CHANNELS_WITHOUT_ADMINS"

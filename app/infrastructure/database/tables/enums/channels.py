from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class ChannelsTableAction(BaseTableActionEnum):
    ADD = "ADD"
    DELETE = "DELETE"
    GET_CHANNEL = "GET_CHANNEL"
    GET_CHANNEL_BY_ID = "GET_CHANNEL_BY_ID"
    UPDATE_CHANNEL = "UPDATE_CHANNEL"
    GET_ALL_CHANNELS = "GET_ALL_CHANNELS"

from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class RSSFeedsTableAction(BaseTableActionEnum):
    ADD = "ADD"
    DELETE = "DELETE"
    GET_FEED_BY_URL = "GET_FEED_BY_URL"
    GET_FEEDS_BY_CHANNEL = "GET_FEEDS_BY_CHANNEL"
    UPDATE_FETCH_STATUS = "UPDATE_FETCH_STATUS"
    UPDATE_ERROR_COUNT = "UPDATE_ERROR_COUNT"
    RESET_ERROR_COUNT = "RESET_ERROR_COUNT"

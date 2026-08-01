from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class RSSPostsTableAction(BaseTableActionEnum):
    ADD = "ADD"
    GET_SENT_GUIDS = "GET_SENT_GUIDS"

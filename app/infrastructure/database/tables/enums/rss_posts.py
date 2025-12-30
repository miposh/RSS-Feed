from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class RSSPostsTableAction(BaseTableActionEnum):
    ADD = "ADD"
    DELETE = "DELETE"
    GET_POST = "GET_POST"
    GET_POST_BY_GUID = "GET_POST_BY_GUID"
    GET_SENT_GUIDS = "GET_SENT_GUIDS"
    GET_UNSENT_POSTS = "GET_UNSENT_POSTS"
    MARK_AS_SENT = "MARK_AS_SENT"
    GET_POSTS_BY_FEED = "GET_POSTS_BY_FEED"

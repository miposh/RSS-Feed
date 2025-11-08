from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class FeedSubscriptionsTableAction(BaseTableActionEnum):
    """Actions for FeedSubscriptionsTable."""
    
    ADD = "ADD"
    DELETE = "DELETE"
    GET_SUBSCRIPTION = "GET_SUBSCRIPTION"
    GET_SUBSCRIPTIONS_BY_FEED = "GET_SUBSCRIPTIONS_BY_FEED"
    GET_SUBSCRIPTIONS_BY_CHANNEL = "GET_SUBSCRIPTIONS_BY_CHANNEL"
    GET_CHANNELS_FOR_FEED = "GET_CHANNELS_FOR_FEED"

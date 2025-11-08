from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.tables.users import UsersTable
from app.infrastructure.database.tables.channels import ChannelsTable
from app.infrastructure.database.tables.rss_feeds import RSSFeedsTable
from app.infrastructure.database.tables.rss_posts import RSSPostsTable
from app.infrastructure.database.tables.feed_subscriptions import FeedSubscriptionsTable


class DB:    
    def __init__(self, connection: BaseConnection) -> None:
        self.connection = connection
        self.users = UsersTable(connection=connection)
        self.channels = ChannelsTable(connection=connection)
        self.rss_feeds = RSSFeedsTable(connection=connection)
        self.rss_posts = RSSPostsTable(connection=connection)
        self.feed_subscriptions = FeedSubscriptionsTable(connection=connection)

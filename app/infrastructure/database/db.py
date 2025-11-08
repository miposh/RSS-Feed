from app.infrastructure.database.connection.base import BaseConnection


class DB:
    """
    Main database class that provides access to all table interfaces.
    Add table instances here as you create them.
    """
    
    def __init__(self, connection: BaseConnection) -> None:
        self.connection = connection
        # TODO: Initialize table classes here
        # Example:
        # from app.infrastructure.database.tables.users import UsersTable
        # self.users = UsersTable(connection=connection)
        # self.feeds = FeedsTable(connection=connection)
        # self.chats = ChatsTable(connection=connection)

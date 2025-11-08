from app.infrastructure.database.tables.enums.base import BaseTableActionEnum


class UsersTableAction(BaseTableActionEnum):
    ADD = "ADD"
    DELETE = "DELETE"
    GET_USER = "GET_USER"
    GET_USER_BY_USERNAME = "GET_USER_BY_USERNAME"
    UPDATE_USERNAME = "UPDATE_USERNAME"
    GET_ALL_USERS = "GET_ALL_USERS"

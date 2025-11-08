from .user_handlers import commands_router

__all__ = ["routers"]

routers = [
    commands_router,
]

from aiogram.enums import ParseMode
from dynaconf import Dynaconf
from pydantic import BaseModel, Field


class LogsConfig(BaseModel):
    level_name: str = Field(
        default="INFO", description="Log level name (e.g. DEBUG, INFO, WARNING, ERROR)."
    )
    format: str = Field(
        default="%(asctime)s [%(levelname)s] %(message)s",
        description="Log message format."
    )


class BotConfig(BaseModel):
    token: str = Field(..., description="Telegram bot API token.")
    parse_mode: ParseMode = Field(
        default=ParseMode.HTML, description="Default parse mode for sending messages (e.g. HTML, Markdown)."
    )


class PostgresConfig(BaseModel):
    name: str = Field(..., description="PostgreSQL database name.")
    host: str = Field(..., description="PostgreSQL server hostname.")
    port: int = Field(..., description="PostgreSQL server port.")
    user: str = Field(..., description="PostgreSQL username.")
    password: str = Field(..., description="PostgreSQL user password.")


class RSSConfig(BaseModel):
    check_interval: int = Field(default=300, description="Interval for checking RSS feeds in seconds.")
    cleanup_interval: int = Field(default=86400, description="Interval for cleanup tasks in seconds.")
    sent_posts_retention_days: int = Field(default=30, description="Days to keep sent posts.")


class AppConfig(BaseModel):
    logs: LogsConfig
    bot: BotConfig
    postgres: PostgresConfig
    rss: RSSConfig


# Инициализация Dynaconf
# Путь относительно корня проекта (где запускается main.py)
_settings = Dynaconf(
    envvar_prefix=False,
    environments=True,
    env_switcher="ENV_FOR_DYNACONF",
    settings_files=["settings.toml", ".secrets.toml"],
    load_dotenv=True,
    root_path=".",  # Корень проекта
)


def get_config() -> AppConfig:
    """
    Returns a typed application configuration.

    Returns:
        AppConfig: A validated Pydantic model containing the application settings.
    """
    logs = LogsConfig(
        level_name=_settings.get("logs.level_name", "INFO"),
        format=_settings.get("logs.format", "%(asctime)s [%(levelname)s] %(message)s"),
    )

    bot = BotConfig(
        token=_settings.bot_token,
        parse_mode=_settings.get("bot.parse_mode", "HTML"),
    )

    postgres = PostgresConfig(
        name=_settings.postgres.name,
        host=_settings.postgres.host,
        port=_settings.postgres.port,
        user=_settings.postgres.user,
        password=_settings.postgres_password,
    )

    rss = RSSConfig(
        check_interval=_settings.get("rss_check_interval", 300),
        cleanup_interval=_settings.get("cleanup_interval", 86400),
        sent_posts_retention_days=_settings.get("sent_posts_retention_days", 30),
    )

    return AppConfig(
        logs=logs,
        bot=bot,
        postgres=postgres,
        rss=rss,
    )

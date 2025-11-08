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


class RedisConfig(BaseModel):
    host: str = Field(default="localhost", description="Redis server hostname.")
    port: int = Field(default=6379, description="Redis server port.")
    database: int = Field(default=0, description="Redis database index.")
    username: str | None = Field(None, description="Optional Redis username.")
    password: str | None = Field(None, description="Optional Redis password.")


class RSSConfig(BaseModel):
    check_interval: int = Field(default=300, description="RSS check interval in seconds.")
    cleanup_interval: int = Field(default=86400, description="Cleanup interval in seconds.")
    sent_posts_retention_days: int = Field(default=30, description="Days to keep sent posts.")


class GeminiConfig(BaseModel):
    enabled: bool = Field(default=False, description="Enable Gemini AI rewriting.")
    api_key: str | None = Field(None, description="Google Gemini API key.")


class ScraperConfig(BaseModel):
    enabled: bool = Field(default=False, description="Enable ScraperAPI.")
    api_key: str | None = Field(None, description="ScraperAPI key.")


class AppConfig(BaseModel):
    logs: LogsConfig
    bot: BotConfig
    postgres: PostgresConfig
    redis: RedisConfig
    rss: RSSConfig
    gemini: GeminiConfig
    scraper: ScraperConfig


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

    redis = RedisConfig(
        host=_settings.get("redis.host", "localhost"),
        port=_settings.get("redis.port", 6379),
        database=_settings.get("redis.database", 0),
        username=_settings.get("redis_username"),
        password=_settings.get("redis_password"),
    )

    rss = RSSConfig(
        check_interval=_settings.get("rss_check_interval", 300),
        cleanup_interval=_settings.get("cleanup_interval", 86400),
        sent_posts_retention_days=_settings.get("sent_posts_retention_days", 30),
    )

    gemini = GeminiConfig(
        enabled=_settings.get("gemini_enabled", False),
        api_key=_settings.get("gemini_api_key"),
    )

    scraper = ScraperConfig(
        enabled=_settings.get("scraper_enabled", False),
        api_key=_settings.get("scraper_api_key"),
    )

    return AppConfig(
        logs=logs,
        bot=bot,
        postgres=postgres,
        redis=redis,
        rss=rss,
        gemini=gemini,
        scraper=scraper,
    )

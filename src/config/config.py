import os
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = str(DATA_DIR / "rss_bot.db")

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

class ConfigError(Exception):
    pass

class Config:
    
    def __init__(self, env_file: str = ".env"):
        
        if not load_dotenv(env_file):
            print(f"Warning: Environment file '{env_file}' not found or empty.")
        
        self._required_vars = ["BOT_TOKEN"]
        self._validate_required_vars()
        
        # Set default values
        self._defaults = {
            "RSS_CHECK_INTERVAL": "300",  # 5 minutes in seconds
            "POST_AGE_LIMIT": "86400",    # 24 hours in seconds
        }

    def _validate_required_vars(self) -> None:
        """Validate that all required environment variables are set."""
        missing = [var for var in self._required_vars if not os.getenv(var)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    def get(self, key: str, default: Any = None) -> Any:
        
        # First check environment variables
        value = os.getenv(key)
        
        # Then check defaults
        if value is None and key in self._defaults:
            value = self._defaults[key]
            
        # Finally use the provided default
        if value is None:
            value = default
            
        return value

    def require(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise ConfigError(f"Required config value '{key}' is missing")
        return value

    @property
    def bot_token(self) -> str:
        """Get the bot token."""
        return self.require("BOT_TOKEN")
        
    @property
    def db_path(self) -> str:
        """Get the database path."""
        return DB_PATH

try:
    config = Config()
except ConfigError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
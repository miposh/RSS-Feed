from dataclasses import dataclass
from typing import Optional


@dataclass
class Group:
    """Model representing a Telegram group."""
    id: Optional[int] = None
    chat_id: int = 0 
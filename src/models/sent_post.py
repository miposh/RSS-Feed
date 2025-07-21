from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SentPost:
    """Model representing a sent post."""
    id: Optional[int] = None
    post_guid: str = ""
    feed_id: int = 0
    sent_at: Optional[datetime] = None 
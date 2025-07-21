from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class RSSPost:
    """Model representing a post from an RSS feed."""
    guid: str
    title: str
    link: str
    summary: str = ""
    published_time: Optional[datetime] = None
    feed_id: int = 0 
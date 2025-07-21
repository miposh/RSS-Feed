from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class RSSFeed:
    """Model representing an RSS feed."""
    id: Optional[int] = None
    url: str = ""
    group_id: int = 0


@dataclass
class RSSPost:
    """Model representing a post from an RSS feed."""
    guid: str
    title: str
    link: str
    summary: str = ""
    published_time: Optional[datetime] = None
    feed_id: int = 0 
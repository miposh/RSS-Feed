"""
Models for RSS parsing (not database models).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class RSSPost:
    """RSS post model for parsing (not for database)."""
    guid: str
    title: str
    link: str
    summary: str = ""
    content: str = ""
    author: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    published_time: Optional[datetime] = None

"""
Models for RSS parsing (not database models).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RSSPost:
    """RSS post model for parsing (not for database)."""
    guid: str
    title: str
    link: str
    summary: str = ""
    content: str = ""
    published_time: Optional[datetime] = None

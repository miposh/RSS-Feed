from dataclasses import dataclass
from typing import Optional


@dataclass
class RSSFeed:
    id: Optional[int] = None
    url: str = ""
    group_id: int = 0
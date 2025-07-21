from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone, timedelta


@dataclass
class SentPost:
    id: Optional[int] = None
    post_guid: str = ""
    feed_id: int = 0
    sent_at: datetime = datetime.now(timezone(timedelta(hours=3))) 
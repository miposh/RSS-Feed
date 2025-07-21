from dataclasses import dataclass
from typing import Optional


@dataclass
class Group:
    id: Optional[int] = None
    chat_id: int = 0 
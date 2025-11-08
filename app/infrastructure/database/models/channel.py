from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChannelModel(BaseModel):
    """Pydantic model for Channel."""
    
    id: int = Field(..., description="Internal auto-incrementing primary key")
    channel_id: int = Field(..., description="Telegram chat/channel ID")
    username: Optional[str] = Field(None, description="Telegram channel username (without @)")
    title: str = Field(..., description="Channel/group title")
    created_at: datetime = Field(..., description="Timestamp of channel creation")

    class Config:
        from_attributes = True
        frozen = True
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "id": 1,
                "channel_id": -1001234567890,
                "username": "my_channel",
                "title": "My Channel",
                "created_at": "2025-01-01T12:00:00+00:00",
            }
        }

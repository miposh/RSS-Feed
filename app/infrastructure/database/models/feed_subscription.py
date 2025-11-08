from datetime import datetime

from pydantic import BaseModel, Field


class FeedSubscriptionModel(BaseModel):
    id: int = Field(..., description="Internal auto-incrementing primary key")
    feed_id: int = Field(..., description="RSS feed reference")
    channel_id: int = Field(..., description="Channel reference")
    created_at: datetime = Field(..., description="Timestamp of subscription creation")

    class Config:
        from_attributes = True
        frozen = True
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "id": 1,
                "feed_id": 1,
                "channel_id": 1,
                "created_at": "2025-01-01T12:00:00+00:00",
            }
        }

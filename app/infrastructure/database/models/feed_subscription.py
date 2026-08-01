from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeedSubscriptionModel(BaseModel):
    id: int = Field(..., description="Internal auto-incrementing primary key")
    feed_id: int = Field(..., description="RSS feed reference")
    channel_id: int = Field(..., description="Channel reference")
    created_at: datetime = Field(..., description="Timestamp of subscription creation")

    model_config = ConfigDict(
        from_attributes=True,
        frozen=True,
        extra="forbid",
    )

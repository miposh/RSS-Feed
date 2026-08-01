from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChannelAdminModel(BaseModel):
    id: int = Field(..., description="Internal auto-incrementing primary key")
    channel_id: int = Field(..., description="Channel internal ID (FK to channels.id)")
    user_id: int = Field(..., description="User internal ID (FK to users.id)")
    synced_at: datetime = Field(..., description="Timestamp of last sync from Telegram API")
    created_at: datetime = Field(..., description="Timestamp of admin record creation")

    model_config = ConfigDict(
        from_attributes=True,
        frozen=True,
        extra="forbid",
    )

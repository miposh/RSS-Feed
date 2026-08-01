from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserModel(BaseModel):
    id: int = Field(..., description="Internal auto-incrementing primary key")
    user_id: int = Field(..., description="Telegram user ID, unique per user")
    username: Optional[str] = Field(None, description="Telegram username (without @)")
    created_at: datetime = Field(..., description="Timestamp of account creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    model_config = ConfigDict(
        from_attributes=True,
        frozen=True,
        extra="forbid",
    )

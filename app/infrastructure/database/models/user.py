from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserModel(BaseModel):
    """Pydantic model for User."""
    
    id: int = Field(..., description="Internal auto-incrementing primary key")
    user_id: int = Field(..., description="Telegram user ID, unique per user")
    username: Optional[str] = Field(None, description="Telegram username (without @)")
    created_at: datetime = Field(..., description="Timestamp of account creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    class Config:
        from_attributes = True
        frozen = True
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123456789,
                "username": "john_doe",
                "created_at": "2025-01-01T12:00:00+00:00",
                "updated_at": "2025-01-01T12:00:00+00:00",
            }
        }

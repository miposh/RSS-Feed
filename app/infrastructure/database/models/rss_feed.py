from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RSSFeedModel(BaseModel):
    """Pydantic model for RSSFeed."""
    
    id: int = Field(..., description="Internal auto-incrementing primary key")
    url: str = Field(..., description="Canonical RSS/Atom feed URL")
    site_url: Optional[str] = Field(None, description="Website URL")
    title: Optional[str] = Field(None, description="Feed title")
    description: Optional[str] = Field(None, description="Feed description")
    language: Optional[str] = Field(None, description="Feed language code")
    image_url: Optional[str] = Field(None, description="Feed image URL")
    etag: Optional[str] = Field(None, description="ETag for conditional fetching")
    last_modified: Optional[datetime] = Field(None, description="Last-Modified header value")
    last_fetched_at: Optional[datetime] = Field(None, description="Last successful fetch time")
    last_status: Optional[int] = Field(None, description="HTTP status code of last fetch")
    error_count: int = Field(0, description="Consecutive error count")
    backoff_until: Optional[datetime] = Field(None, description="Backoff timestamp")
    fetch_interval_sec: int = Field(900, description="Fetch interval in seconds")
    enabled: bool = Field(True, description="Whether feed is active")
    owner_user_id: Optional[int] = Field(None, description="User who added this feed")
    created_at: datetime = Field(..., description="Timestamp of feed creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")

    class Config:
        from_attributes = True
        frozen = True
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "id": 1,
                "url": "https://example.com/feed.xml",
                "site_url": "https://example.com",
                "title": "Example Feed",
                "description": "An example RSS feed",
                "language": "en",
                "image_url": None,
                "etag": None,
                "last_modified": None,
                "last_fetched_at": "2025-01-01T12:00:00+00:00",
                "last_status": 200,
                "error_count": 0,
                "backoff_until": None,
                "fetch_interval_sec": 900,
                "enabled": True,
                "owner_user_id": 1,
                "created_at": "2025-01-01T12:00:00+00:00",
                "updated_at": "2025-01-01T12:00:00+00:00",
            }
        }

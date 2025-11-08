from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class RSSPostModel(BaseModel):
    """Pydantic model for RSSPost."""
    
    id: int = Field(..., description="Internal auto-incrementing primary key")
    feed_id: int = Field(..., description="RSS feed reference")
    guid: str = Field(..., description="GUID/ID from feed item")
    link: str = Field(..., description="Post URL")
    title: Optional[str] = Field(None, description="Post title")
    summary: Optional[str] = Field(None, description="Post summary")
    content_html: Optional[str] = Field(None, description="Raw HTML content")
    author: Optional[str] = Field(None, description="Post author")
    published_at: Optional[datetime] = Field(None, description="Publication date from feed")
    created_at: datetime = Field(..., description="When this post was fetched")
    fetched_at: datetime = Field(..., description="When this post was fetched")
    content_hash: Optional[str] = Field(None, description="SHA1 hash of normalized content")
    media_urls: Optional[dict[str, Any]] = Field(None, description="List of media/image URLs")
    tags: Optional[dict[str, Any]] = Field(None, description="Post tags/categories")
    is_sent: bool = Field(False, description="Whether post has been sent")
    sent_at: Optional[datetime] = Field(None, description="When post was sent")

    class Config:
        from_attributes = True
        frozen = True
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "id": 1,
                "feed_id": 1,
                "guid": "https://example.com/post/123",
                "link": "https://example.com/post/123",
                "title": "Example Post",
                "summary": "This is an example post",
                "content_html": "<p>This is an example post</p>",
                "author": "John Doe",
                "published_at": "2025-01-01T12:00:00+00:00",
                "created_at": "2025-01-01T12:00:00+00:00",
                "fetched_at": "2025-01-01T12:00:00+00:00",
                "content_hash": "abc123",
                "media_urls": {"images": ["https://example.com/image.jpg"]},
                "tags": {"categories": ["tech", "news"]},
                "is_sent": False,
                "sent_at": None,
            }
        }

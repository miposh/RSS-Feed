from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field


class RSSPostModel(BaseModel):
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

    model_config = ConfigDict(
        from_attributes=True,
        frozen=True,
        extra="forbid",
    )

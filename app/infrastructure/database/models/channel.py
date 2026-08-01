from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


ScraperTypeValue = Literal["scraperapi", "botasaurus"]


class ChannelModel(BaseModel):
    id: int = Field(..., description="Internal auto-incrementing primary key")
    channel_id: int = Field(..., description="Telegram chat/channel ID")
    username: Optional[str] = Field(None, description="Telegram channel username (without @)")
    title: str = Field(..., description="Channel/group title")
    parsing_is_enabled: bool = Field(False, description="Whether RSS parsing is enabled for this channel")
    interval_time: int = Field(300, description="RSS feed check interval in seconds (default: 300 = 5 minutes)")
    scraper_is_enabled: bool = Field(True, description="Whether to use scraper API for full article extraction")
    scraper_type: ScraperTypeValue = Field("botasaurus", description="Type of scraper: scraperapi or botasaurus")
    scraper_api_key: Optional[str] = Field(None, description="API key for scraper service (required for scraperapi)")
    created_at: datetime = Field(..., description="Timestamp of channel creation")

    model_config = ConfigDict(
        from_attributes=True,
        frozen=True,
        extra="forbid",
    )

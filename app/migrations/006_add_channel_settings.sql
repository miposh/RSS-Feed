-- Add channel settings
-- Revision ID: 006
-- Create Date: 2025-11-09

-- Add interval_time and scraper settings to channels table
ALTER TABLE channels
ADD COLUMN IF NOT EXISTS interval_time INTEGER NOT NULL DEFAULT 300,
ADD COLUMN IF NOT EXISTS scraper_is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS scraper_api_key TEXT;

-- Add comment for interval_time
COMMENT ON COLUMN channels.interval_time IS 'RSS feed check interval in seconds (default: 300 = 5 minutes)';
COMMENT ON COLUMN channels.scraper_is_enabled IS 'Whether to use scraper API for full article extraction';
COMMENT ON COLUMN channels.scraper_api_key IS 'API key for scraper service (optional, can use global key)';

-- Create index for interval_time for efficient filtering
CREATE INDEX IF NOT EXISTS idx_channels_interval_time ON channels(interval_time);

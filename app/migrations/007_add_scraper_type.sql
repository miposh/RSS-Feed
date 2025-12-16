-- Add scraper_type column to channels table
-- Revision ID: 007
-- Create Date: 2025-12-16

-- Add scraper_type column to channels table
-- Values: 'scraperapi', 'botasaurus'
ALTER TABLE channels
ADD COLUMN IF NOT EXISTS scraper_type VARCHAR(20) NOT NULL DEFAULT 'botasaurus';

-- Add comment for scraper_type
COMMENT ON COLUMN channels.scraper_type IS 'Type of scraper to use: scraperapi or botasaurus';

-- Create index for scraper_type for efficient filtering
CREATE INDEX IF NOT EXISTS idx_channels_scraper_type ON channels(scraper_type);

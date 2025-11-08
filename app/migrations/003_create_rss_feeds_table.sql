-- Create rss_feeds table
-- Revision ID: 003
-- Create Date: 2025-11-08

CREATE TABLE IF NOT EXISTS rss_feeds (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    site_url TEXT,
    title TEXT,
    description TEXT,
    language VARCHAR(16),
    image_url TEXT,
    etag TEXT,
    last_modified TIMESTAMPTZ,
    last_fetched_at TIMESTAMPTZ,
    last_status INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0,
    backoff_until TIMESTAMPTZ,
    fetch_interval_sec INTEGER NOT NULL DEFAULT 900,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    owner_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_fetch_interval_positive CHECK (fetch_interval_sec > 0),
    CONSTRAINT ck_error_count_non_negative CHECK (error_count >= 0)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_rss_feeds_owner_user_id ON rss_feeds(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_rss_feeds_enabled ON rss_feeds(enabled);
CREATE INDEX IF NOT EXISTS idx_rss_feeds_scheduler ON rss_feeds(enabled, backoff_until, last_fetched_at);

-- Create trigger for updated_at
CREATE TRIGGER update_rss_feeds_updated_at
    BEFORE UPDATE ON rss_feeds
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create rss_posts table
-- Revision ID: 005
-- Create Date: 2025-11-08

CREATE TABLE IF NOT EXISTS rss_posts (
    id BIGSERIAL PRIMARY KEY,
    feed_id BIGINT NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
    guid TEXT NOT NULL,
    link TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    content_html TEXT,
    author TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash VARCHAR(40),
    media_urls JSONB,
    tags JSONB,
    is_sent BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    CONSTRAINT uq_feed_guid UNIQUE (feed_id, guid)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_rss_posts_feed_id ON rss_posts(feed_id);
CREATE INDEX IF NOT EXISTS idx_rss_posts_feed_published ON rss_posts(feed_id, published_at);
CREATE INDEX IF NOT EXISTS idx_rss_posts_is_sent_published ON rss_posts(is_sent, published_at);
CREATE INDEX IF NOT EXISTS idx_rss_posts_content_hash ON rss_posts(content_hash);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_rss_posts_media_urls ON rss_posts USING GIN (media_urls);
CREATE INDEX IF NOT EXISTS idx_rss_posts_tags ON rss_posts USING GIN (tags);

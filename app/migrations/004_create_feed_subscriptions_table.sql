-- Create feed_subscriptions table
-- Revision ID: 004
-- Create Date: 2025-11-08

CREATE TABLE IF NOT EXISTS feed_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    feed_id BIGINT NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_feed_channel UNIQUE (feed_id, channel_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_feed_subscriptions_feed_id ON feed_subscriptions(feed_id);
CREATE INDEX IF NOT EXISTS idx_feed_subscriptions_channel_id ON feed_subscriptions(channel_id);

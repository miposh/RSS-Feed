-- Migration 001: Add indexes for performance optimization
-- Date: 2025-10-14
-- Description: Add critical indexes for deduplication and cleanup queries

-- Index for fast post deduplication lookups
-- This is the most critical index for performance (used on every post check)
CREATE INDEX IF NOT EXISTS idx_sent_posts_feed_guid 
ON sent_posts(feed_id, guid);

-- Index for cleanup queries (deleting old posts)
CREATE INDEX IF NOT EXISTS idx_sent_posts_sent_at 
ON sent_posts(sent_at);

-- Composite index for has_sent_posts_for_feed query
CREATE INDEX IF NOT EXISTS idx_sent_posts_feed_id
ON sent_posts(feed_id);

-- Analyze tables to update statistics for query planner
ANALYZE sent_posts;
ANALYZE rss_feeds;
ANALYZE groups;

-- Vacuum to reclaim space (optional, can be run separately)
-- VACUUM;

-- Migration to new schema with AI rewrite support
-- Run this migration to upgrade from old schema to new one

-- ============================================================================
-- PRAGMA settings
-- ============================================================================
PRAGMA foreign_keys = OFF;

-- ============================================================================
-- Backup old tables
-- ============================================================================
ALTER TABLE groups RENAME TO groups_old;
ALTER TABLE rss_feeds RENAME TO rss_feeds_old;
ALTER TABLE sent_posts RENAME TO sent_posts_old;

-- ============================================================================
-- 1. RSS Feeds
-- ============================================================================
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    last_modified TEXT,  -- HTTP Last-Modified header
    etag TEXT,           -- HTTP ETag header
    pull_interval INTEGER NOT NULL DEFAULT 300,  -- seconds
    active INTEGER NOT NULL DEFAULT 1,           -- boolean: 1=active, 0=disabled
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX idx_feeds_active ON feeds(active);
CREATE INDEX idx_feeds_updated_at ON feeds(updated_at);

-- ============================================================================
-- 2. Feed Items (News/Posts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    guid TEXT NOT NULL,              -- RSS item GUID/ID
    url TEXT,                        -- canonical URL
    title TEXT NOT NULL,
    summary TEXT,
    content_hash TEXT,               -- MD5/SHA256 of content for deduplication
    published_at TEXT,               -- ISO-8601 UTC
    raw_content TEXT,                -- Full original content
    processed INTEGER NOT NULL DEFAULT 0,  -- boolean: ready for rewrite
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE,
    UNIQUE(feed_id, guid)
);

CREATE INDEX idx_items_feed_id ON items(feed_id);
CREATE INDEX idx_items_processed ON items(processed);
CREATE INDEX idx_items_published_at ON items(published_at DESC);
CREATE INDEX idx_items_content_hash ON items(content_hash);

-- ============================================================================
-- 3. AI Rewrites
-- ============================================================================
CREATE TABLE IF NOT EXISTS rewrites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,
    rewritten_title TEXT,
    rewritten_text TEXT,
    bullets_json TEXT,               -- JSON array of key points
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'queued',  -- queued|processing|done|failed
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX idx_rewrites_status ON rewrites(status);
CREATE INDEX idx_rewrites_item_id ON rewrites(item_id);

-- ============================================================================
-- 4. Telegram Chats/Channels
-- ============================================================================
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,  -- Telegram chat_id (INT64)
    title TEXT,
    username TEXT,
    chat_type TEXT DEFAULT 'group',   -- private|group|supergroup|channel
    ai_enabled INTEGER NOT NULL DEFAULT 0,  -- boolean: use AI rewrite (disabled by default)
    language TEXT DEFAULT 'ru',             -- ISO 639-1 code
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX idx_chats_chat_id ON chats(chat_id);
CREATE INDEX idx_chats_ai_enabled ON chats(ai_enabled);

-- ============================================================================
-- 5. Subscriptions (Many-to-Many: Chats <-> Feeds)
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    feed_id INTEGER NOT NULL,
    filters_json TEXT,               -- JSON: {"keywords": [], "exclude": []}
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE,
    UNIQUE(chat_id, feed_id)
);

CREATE INDEX idx_subscriptions_chat_id ON subscriptions(chat_id);
CREATE INDEX idx_subscriptions_feed_id ON subscriptions(feed_id);
CREATE INDEX idx_subscriptions_active ON subscriptions(active);

-- ============================================================================
-- 6. Deliveries (Message Sending Log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    message_id INTEGER,              -- Telegram message_id (null if failed)
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|sent|failed
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    sent_at TEXT,                    -- ISO-8601 UTC
    duration_ms INTEGER,             -- API call duration
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    UNIQUE(chat_id, item_id)
);

CREATE INDEX idx_deliveries_chat_id ON deliveries(chat_id);
CREATE INDEX idx_deliveries_item_id ON deliveries(item_id);
CREATE INDEX idx_deliveries_status ON deliveries(status);
CREATE INDEX idx_deliveries_sent_at ON deliveries(sent_at DESC);

-- ============================================================================
-- 7. Error Log
-- ============================================================================
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context TEXT NOT NULL,           -- e.g., 'rss_fetch', 'ai_rewrite', 'telegram_send'
    message TEXT NOT NULL,
    traceback TEXT,
    related_table TEXT,              -- e.g., 'feeds', 'items'
    related_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX idx_errors_context ON errors(context);
CREATE INDEX idx_errors_created_at ON errors(created_at DESC);
CREATE INDEX idx_errors_related ON errors(related_table, related_id);

-- ============================================================================
-- 8. Daily Metrics (Aggregated)
-- ============================================================================
CREATE TABLE IF NOT EXISTS metrics_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,       -- YYYY-MM-DD
    items_processed INTEGER DEFAULT 0,
    rewrites_done INTEGER DEFAULT 0,
    ai_cost_usd REAL DEFAULT 0.0,
    messages_sent INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0
);

CREATE INDEX idx_metrics_date ON metrics_daily(date DESC);

-- ============================================================================
-- Triggers for auto-updating updated_at
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS update_feeds_timestamp 
AFTER UPDATE ON feeds
BEGIN
    UPDATE feeds SET updated_at = datetime('now', 'utc') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_rewrites_timestamp 
AFTER UPDATE ON rewrites
BEGIN
    UPDATE rewrites SET updated_at = datetime('now', 'utc') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_chats_timestamp 
AFTER UPDATE ON chats
BEGIN
    UPDATE chats SET updated_at = datetime('now', 'utc') WHERE id = NEW.id;
END;

-- ============================================================================
-- Migrate data from old tables
-- ============================================================================

-- Migrate feeds from old rss_feeds table
INSERT INTO feeds (id, url, title, active, created_at, updated_at)
SELECT DISTINCT 
    rf.id,
    rf.url,
    NULL as title,
    1 as active,
    datetime('now', 'utc'),
    datetime('now', 'utc')
FROM rss_feeds_old rf;

-- Migrate chats from old groups table
INSERT INTO chats (chat_id, title, chat_type, created_at, updated_at)
SELECT DISTINCT
    g.chat_id,
    CAST(g.chat_id AS TEXT) as title,
    'group' as chat_type,
    datetime('now', 'utc'),
    datetime('now', 'utc')
FROM groups_old g;

-- Migrate subscriptions
INSERT INTO subscriptions (chat_id, feed_id, active, created_at)
SELECT 
    c.id as chat_id,
    rf.id as feed_id,
    1 as active,
    datetime('now', 'utc')
FROM rss_feeds_old rf
JOIN groups_old g ON g.id = rf.group_id
JOIN chats c ON c.chat_id = g.chat_id;

-- Note: sent_posts will be migrated to deliveries when items are created during RSS parsing

-- ============================================================================
-- Drop old tables
-- ============================================================================
DROP TABLE IF EXISTS sent_posts_old;
DROP TABLE IF EXISTS rss_feeds_old;
DROP TABLE IF EXISTS groups_old;

-- ============================================================================
-- Re-enable foreign keys
-- ============================================================================
PRAGMA foreign_keys = ON;

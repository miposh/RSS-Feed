CREATE_TABLES_SQL = """
-- ============================================================================
-- 1. RSS Feeds
-- ============================================================================
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    last_modified TEXT,
    etag TEXT,
    pull_interval INTEGER NOT NULL DEFAULT 300,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_feeds_active ON feeds(active);
CREATE INDEX IF NOT EXISTS idx_feeds_updated_at ON feeds(updated_at);

-- ============================================================================
-- 2. Feed Items (News/Posts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    guid TEXT NOT NULL,
    url TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    content_hash TEXT,
    published_at TEXT,
    raw_content TEXT,
    processed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE,
    UNIQUE(feed_id, guid)
);

CREATE INDEX IF NOT EXISTS idx_items_feed_id ON items(feed_id);
CREATE INDEX IF NOT EXISTS idx_items_processed ON items(processed);
CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_content_hash ON items(content_hash);

-- ============================================================================
-- 3. AI Rewrites
-- ============================================================================
CREATE TABLE IF NOT EXISTS rewrites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,
    rewritten_title TEXT,
    rewritten_text TEXT,
    bullets_json TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rewrites_status ON rewrites(status);
CREATE INDEX IF NOT EXISTS idx_rewrites_item_id ON rewrites(item_id);

-- ============================================================================
-- 4. Telegram Chats/Channels
-- ============================================================================
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,
    title TEXT,
    username TEXT,
    chat_type TEXT DEFAULT 'group',
    ai_enabled INTEGER NOT NULL DEFAULT 0,
    language TEXT DEFAULT 'ru',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats(chat_id);
CREATE INDEX IF NOT EXISTS idx_chats_ai_enabled ON chats(ai_enabled);

-- ============================================================================
-- 5. Subscriptions (Many-to-Many: Chats <-> Feeds)
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    feed_id INTEGER NOT NULL,
    filters_json TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE,
    UNIQUE(chat_id, feed_id)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_chat_id ON subscriptions(chat_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_feed_id ON subscriptions(feed_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(active);

-- ============================================================================
-- 6. Deliveries (Message Sending Log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    message_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    sent_at TEXT,
    duration_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    UNIQUE(chat_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_deliveries_chat_id ON deliveries(chat_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_item_id ON deliveries(item_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS idx_deliveries_sent_at ON deliveries(sent_at DESC);

-- ============================================================================
-- 7. Error Log
-- ============================================================================
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context TEXT NOT NULL,
    message TEXT NOT NULL,
    traceback TEXT,
    related_table TEXT,
    related_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_errors_context ON errors(context);
CREATE INDEX IF NOT EXISTS idx_errors_created_at ON errors(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_errors_related ON errors(related_table, related_id);

-- ============================================================================
-- 8. Users (Telegram Users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ============================================================================
-- 9. Daily Metrics (Aggregated)
-- ============================================================================
CREATE TABLE IF NOT EXISTS metrics_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    items_processed INTEGER DEFAULT 0,
    rewrites_done INTEGER DEFAULT 0,
    ai_cost_usd REAL DEFAULT 0.0,
    messages_sent INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics_daily(date DESC);
"""

CREATE_TRIGGERS_SQL = """
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
"""

PRAGMA_SETTINGS = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA temp_store = MEMORY;
PRAGMA foreign_keys = ON;
"""

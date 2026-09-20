-- Checks the feed error-backoff SQL from app/infrastructure/database/tables/rss_feeds.py.
-- Runs on temp tables, so point it at any throwaway Postgres:
--   psql -f tests/sql/backoff_check.sql
-- Expect: in_backoff=t, picked_up=0, picked_up_after_reset=1

CREATE TEMP TABLE rss_feeds (
    id BIGSERIAL PRIMARY KEY, url TEXT NOT NULL UNIQUE, site_url TEXT, title TEXT,
    description TEXT, language VARCHAR(16), image_url TEXT, etag TEXT,
    last_modified TIMESTAMPTZ, last_fetched_at TIMESTAMPTZ, last_status INTEGER,
    error_count INTEGER NOT NULL DEFAULT 0, backoff_until TIMESTAMPTZ,
    fetch_interval_sec INTEGER NOT NULL DEFAULT 900, enabled BOOLEAN NOT NULL DEFAULT TRUE,
    owner_user_id BIGINT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_error_count_non_negative CHECK (error_count >= 0)
);
CREATE TEMP TABLE feed_subscriptions (feed_id BIGINT, channel_id BIGINT);
INSERT INTO rss_feeds (url) VALUES ('https://infobali.co.id/feed/');
INSERT INTO feed_subscriptions VALUES (1, 42);

-- three consecutive failures (the real UPDATE statement)
DO $$ BEGIN FOR i IN 1..3 LOOP
  UPDATE rss_feeds
  SET error_count = error_count + 1,
      backoff_until = now() + LEAST(
          INTERVAL '6 hours',
          (fetch_interval_sec * POWER(2, LEAST(error_count, 10)))
              * INTERVAL '1 second'
      )
  WHERE id = 1;
END LOOP; END $$;
SELECT error_count, backoff_until > now() AS in_backoff,
       backoff_until - now() AS wait FROM rss_feeds;

-- the real scheduler filter: feed must now be skipped
SELECT count(*) AS picked_up FROM rss_feeds f
JOIN feed_subscriptions fs ON fs.feed_id = f.id
WHERE fs.channel_id = 42
  AND f.enabled = TRUE AND (f.backoff_until IS NULL OR f.backoff_until <= now());

-- after success it must come back
UPDATE rss_feeds SET error_count = 0, backoff_until = NULL WHERE id = 1;
SELECT count(*) AS picked_up_after_reset FROM rss_feeds f
JOIN feed_subscriptions fs ON fs.feed_id = f.id
WHERE fs.channel_id = 42
  AND f.enabled = TRUE AND (f.backoff_until IS NULL OR f.backoff_until <= now());

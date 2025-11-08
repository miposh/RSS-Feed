-- Create channels table
-- Revision ID: 002
-- Create Date: 2025-11-08

CREATE TABLE IF NOT EXISTS channels (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(32),
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_channels_channel_id ON channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_channels_username ON channels(username);

-- Create channel_admins table (many-to-many: users <-> channels)
-- Revision ID: 008
-- Create Date: 2026-03-19

CREATE TABLE IF NOT EXISTS channel_admins (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_channel_admin UNIQUE (channel_id, user_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_channel_admins_channel_id ON channel_admins(channel_id);
CREATE INDEX IF NOT EXISTS idx_channel_admins_user_id ON channel_admins(user_id);

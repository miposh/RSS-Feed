-- Migration: Add users table
-- Date: 2025-10-14

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

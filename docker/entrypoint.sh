#!/bin/sh
set -eu

log() {
  printf '%s %s\n' "[entrypoint]" "$*"
}

cd /app

if [ "${AUTO_GENERATE_SECRETS_TOML:-1}" = "1" ]; then
  log "Generating .secrets.toml from environment variables (if provided)"
  python - <<'PY'
import json
import os
from pathlib import Path

def q(value: str) -> str:
    return json.dumps(value)

env = os.environ

lines: list[str] = ["[default]"]

if env.get("BOT_TOKEN"):
    lines.append(f"bot_token = {q(env['BOT_TOKEN'])}")

if env.get("POSTGRES_PASSWORD"):
    lines.append(f"postgres_password = {q(env['POSTGRES_PASSWORD'])}")

if env.get("RSS_CHECK_INTERVAL"):
    lines.append(f"rss_check_interval = {int(env['RSS_CHECK_INTERVAL'])}")

if env.get("CLEANUP_INTERVAL"):
    lines.append(f"cleanup_interval = {int(env['CLEANUP_INTERVAL'])}")

if env.get("SENT_POSTS_RETENTION_DAYS"):
    lines.append(f"sent_posts_retention_days = {int(env['SENT_POSTS_RETENTION_DAYS'])}")

lines.extend([
    "",
    "[default.logs]",
    f"level_name = {q(env.get('LOG_LEVEL_NAME', 'INFO'))}",
    "",
    "[default.bot]",
    f'parse_mode = {q(env.get("BOT_PARSE_MODE", "HTML"))}',
    "",
    "[default.postgres]",
    f"name = {q(env.get('POSTGRES_DB', 'rss_bot'))}",
    f"host = {q(env.get('POSTGRES_HOST', 'db'))}",
    f"port = {int(env.get('POSTGRES_PORT', '5432'))}",
    f"user = {q(env.get('POSTGRES_USER', 'postgres'))}",
    "",
])

Path(".secrets.toml").write_text("\n".join(lines), encoding="utf-8")
PY
fi

if [ ! -f .secrets.toml ]; then
  log "WARNING: .secrets.toml not found. App will rely on existing settings/env only."
fi

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
  log "Waiting for PostgreSQL ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}"
  python - <<'PY'
import os
import socket
import time
import sys

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
timeout = int(os.getenv("WAIT_FOR_DB_TIMEOUT", "90"))

deadline = time.time() + timeout
last_error = None

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"[entrypoint] PostgreSQL is reachable at {host}:{port}")
            sys.exit(0)
    except OSError as exc:
        last_error = exc
        time.sleep(2)

print(f"[entrypoint] ERROR: PostgreSQL is not reachable after {timeout}s: {last_error}", file=sys.stderr)
sys.exit(1)
PY
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  log "Applying database migrations"
  python apply_migrations.py
fi

log "Starting application: $*"
exec "$@"


#!/bin/bash
# Cron script to restart the RSS bot container every 2 hours
# Add to crontab: 0 */2 * * * /path/to/restart-cron.sh

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR" || exit 1

echo "[$(date)] Restarting app container..."
docker compose -f "$COMPOSE_FILE" restart app

echo "[$(date)] Restart complete"

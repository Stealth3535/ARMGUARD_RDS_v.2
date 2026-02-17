#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/armguard}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups/production}"
SERVICE_NAME="${SERVICE_NAME:-gunicorn-armguard}"
SECONDARY_SERVICE="${SECONDARY_SERVICE:-armguard-daphne}"

echo "[rollback] Starting rollback at $(date -Iseconds)"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "[rollback] ERROR: backup directory does not exist: $BACKUP_DIR"
  exit 1
fi

LATEST_BACKUP="$(ls -1t "$BACKUP_DIR"/prod-app-*.tgz 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST_BACKUP" ]; then
  echo "[rollback] ERROR: no production backup archives found in $BACKUP_DIR"
  exit 1
fi

echo "[rollback] Restoring from $LATEST_BACKUP"
rm -rf "$PROJECT_DIR"/*
tar -xzf "$LATEST_BACKUP" -C "$PROJECT_DIR"

systemctl restart "$SERVICE_NAME"
if [ -n "$SECONDARY_SERVICE" ]; then
  systemctl restart "$SECONDARY_SERVICE"
fi

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[rollback] ERROR: service failed to start after rollback: $SERVICE_NAME"
  systemctl status "$SERVICE_NAME" --no-pager || true
  exit 1
fi

echo "[rollback] Rollback completed successfully at $(date -Iseconds)"

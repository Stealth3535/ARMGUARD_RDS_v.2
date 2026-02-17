#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/armguard}"
BRANCH="${BRANCH:-main}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env.production}"
SERVICE_NAME="${SERVICE_NAME:-gunicorn-armguard}"
SECONDARY_SERVICE="${SECONDARY_SERVICE:-armguard-daphne}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups/production}"
BACKUP_RETENTION="${BACKUP_RETENTION:-20}"
LOG_DIR="${LOG_DIR:-/var/log/armguard}"
LOG_FILE="${LOG_DIR}/deploy-production-$(date +%Y%m%d_%H%M%S).log"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-core.settings_production}"

mkdir -p "$BACKUP_DIR" "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

ROLLBACK_ARCHIVE=""

rollback_on_failure() {
  echo "[production] Deployment failed, starting rollback"
  if [ -n "$ROLLBACK_ARCHIVE" ] && [ -f "$ROLLBACK_ARCHIVE" ]; then
    rm -rf "$PROJECT_DIR"/*
    tar -xzf "$ROLLBACK_ARCHIVE" -C "$PROJECT_DIR"
    systemctl restart "$SERVICE_NAME" || true
    if [ -n "$SECONDARY_SERVICE" ]; then
      systemctl restart "$SECONDARY_SERVICE" || true
    fi
    echo "[production] Rollback completed from $ROLLBACK_ARCHIVE"
  else
    echo "[production] No rollback archive found; manual intervention required"
  fi
}

trap rollback_on_failure ERR

echo "[production] Starting deployment at $(date -Iseconds)"
echo "[production] Project dir: $PROJECT_DIR"
echo "[production] Branch: $BRANCH"

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "[production] ERROR: $PROJECT_DIR is not a git working tree"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
  echo "[production] ERROR: manage.py not found in $PROJECT_DIR"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "[production] ERROR: environment file not found: $ENV_FILE"
  exit 1
fi

ROLLBACK_ARCHIVE="$BACKUP_DIR/prod-app-$(date +%Y%m%d_%H%M%S).tgz"
echo "[production] Creating backup: $ROLLBACK_ARCHIVE"
tar --exclude='backups' --exclude='.git' --exclude='.venv' -czf "$ROLLBACK_ARCHIVE" -C "$PROJECT_DIR" .

cd "$PROJECT_DIR"

echo "[production] Updating source from origin/$BRANCH"
git fetch --all --prune
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ ! -d ".venv" ]; then
  echo "[production] Creating .venv"
  python3 -m venv .venv
fi

echo "[production] Installing dependencies"
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[production] Loading environment file"
set -a
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE

echo "[production] Running migrations and static collection"
python manage.py migrate --settings="$DJANGO_SETTINGS_MODULE"
python manage.py collectstatic --noinput --settings="$DJANGO_SETTINGS_MODULE"
python manage.py check --settings="$DJANGO_SETTINGS_MODULE"

echo "[production] Restarting services"
systemctl restart "$SERVICE_NAME"
if [ -n "$SECONDARY_SERVICE" ]; then
  systemctl restart "$SECONDARY_SERVICE"
fi

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[production] ERROR: $SERVICE_NAME is not active"
  systemctl status "$SERVICE_NAME" --no-pager || true
  exit 1
fi

find "$BACKUP_DIR" -type f -name 'prod-app-*.tgz' | sort | head -n -"$BACKUP_RETENTION" | xargs -r rm -f

trap - ERR
echo "[production] Deployment completed successfully at $(date -Iseconds)"

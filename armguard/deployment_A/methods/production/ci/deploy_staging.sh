#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/armguard}"
BRANCH="${BRANCH:-main}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env.staging}"
SERVICE_NAME="${SERVICE_NAME:-armguard-staging}"
SECONDARY_SERVICE="${SECONDARY_SERVICE:-}"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups/staging}"
BACKUP_RETENTION="${BACKUP_RETENTION:-10}"
LOG_DIR="${LOG_DIR:-/var/log/armguard}"
LOG_FILE="${LOG_DIR}/deploy-staging-$(date +%Y%m%d_%H%M%S).log"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-core.settings_production}"

mkdir -p "$BACKUP_DIR" "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[staging] Starting deployment at $(date -Iseconds)"
echo "[staging] Project dir: $PROJECT_DIR"
echo "[staging] Branch: $BRANCH"

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "[staging] ERROR: $PROJECT_DIR is not a git working tree"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
  echo "[staging] ERROR: manage.py not found in $PROJECT_DIR"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "[staging] ERROR: environment file not found: $ENV_FILE"
  exit 1
fi

ARCHIVE_FILE="$BACKUP_DIR/staging-app-$(date +%Y%m%d_%H%M%S).tgz"
echo "[staging] Creating backup: $ARCHIVE_FILE"
tar --exclude='backups' --exclude='.git' --exclude='.venv' -czf "$ARCHIVE_FILE" -C "$PROJECT_DIR" .

cd "$PROJECT_DIR"

echo "[staging] Updating source from origin/$BRANCH"
git fetch --all --prune
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ ! -d ".venv" ]; then
  echo "[staging] Creating .venv"
  python3 -m venv .venv
fi

echo "[staging] Installing dependencies"
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[staging] Loading environment file"
set -a
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE

echo "[staging] Running migrations and static collection"
python manage.py migrate --settings="$DJANGO_SETTINGS_MODULE"
python manage.py collectstatic --noinput --settings="$DJANGO_SETTINGS_MODULE"
python manage.py check --settings="$DJANGO_SETTINGS_MODULE"

echo "[staging] Restarting services"
systemctl restart "$SERVICE_NAME"
if [ -n "$SECONDARY_SERVICE" ]; then
  systemctl restart "$SECONDARY_SERVICE"
fi

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[staging] ERROR: $SERVICE_NAME is not active"
  systemctl status "$SERVICE_NAME" --no-pager || true
  exit 1
fi

find "$BACKUP_DIR" -type f -name 'staging-app-*.tgz' | sort | head -n -"$BACKUP_RETENTION" | xargs -r rm -f

echo "[staging] Deployment completed successfully at $(date -Iseconds)"

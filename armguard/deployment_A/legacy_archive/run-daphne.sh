#!/bin/bash
###############################################################################
# Daphne ASGI Server Runner
# Runs Daphne for WebSocket support instead of Gunicorn
###############################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/armguard"
VENV_DIR="$PROJECT_DIR/venv"
APP_MODULE="core.asgi:application"
BIND_ADDRESS="0.0.0.0"
BIND_PORT="8000"
WORKERS="4"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daphne.log"
PID_FILE="$PROJECT_DIR/daphne.pid"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Daphne is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        print_warning "Daphne is already running (PID: $OLD_PID)"
        echo "Stop it first with: kill $OLD_PID"
        exit 1
    else
        print_warning "Stale PID file found, removing..."
        rm "$PID_FILE"
    fi
fi

# Change to project directory
cd "$PROJECT_DIR/armguard" || exit 1

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check if Redis is running (required for channels)
if ! redis-cli ping > /dev/null 2>&1; then
    print_error "Redis is not running!"
    print_info "Start Redis with: sudo systemctl start redis"
    exit 1
fi

print_info "Starting Daphne ASGI server..."
print_info "Binding to: $BIND_ADDRESS:$BIND_PORT"
print_info "Workers: $WORKERS"
print_info "Log file: $LOG_FILE"

# Run Daphne
daphne \
    --bind "$BIND_ADDRESS" \
    --port "$BIND_PORT" \
    --workers "$WORKERS" \
    --proxy-headers \
    --verbosity 2 \
    --access-log "$LOG_FILE" \
    --pid-file "$PID_FILE" \
    "$APP_MODULE" \
    >> "$LOG_FILE" 2>&1 &

DAPHNE_PID=$!
echo "$DAPHNE_PID" > "$PID_FILE"

# Wait a moment and check if it started successfully
sleep 2

if ps -p "$DAPHNE_PID" > /dev/null 2>&1; then
    print_info "Daphne started successfully (PID: $DAPHNE_PID)"
    print_info "WebSocket connections are now available"
    echo ""
    print_info "Logs: tail -f $LOG_FILE"
    print_info "Stop: kill $DAPHNE_PID"
    print_info "Status: ps -p $DAPHNE_PID"
else
    print_error "Failed to start Daphne"
    print_info "Check logs: tail -100 $LOG_FILE"
    exit 1
fi

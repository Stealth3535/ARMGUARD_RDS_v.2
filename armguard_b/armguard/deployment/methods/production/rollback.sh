#!/bin/bash

################################################################################
# ArmGuard Rollback Script
# 
# Safely rollback to a previous backup
# Usage: sudo bash deployment/rollback.sh [backup_file]
################################################################################

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Trap for cleanup
cleanup() {
    if [ -f "/tmp/rollback.lock" ]; then
        rm -f "/tmp/rollback.lock"
    fi
}
trap cleanup EXIT

# Prevent multiple rollback instances
if [ -f "/tmp/rollback.lock" ]; then
    echo "ERROR: Another rollback operation is in progress"
    exit 1
fi
touch "/tmp/rollback.lock"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    source "$SCRIPT_DIR/config.sh"
fi

# Configuration (can be overridden by config.sh)
PROJECT_DIR="${PROJECT_DIR:-/var/www/armguard}"
BACKUP_DIR="${BACKUP_DIR:-/var/www/armguard/backups}"
SERVICE_NAME="${SERVICE_NAME:-gunicorn-armguard}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Print banner
clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║              ${YELLOW}ArmGuard Rollback Utility${CYAN}                    ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║  ${RED}⚠  WARNING: This will restore from a backup${CYAN}           ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}ERROR: Backup directory not found: $BACKUP_DIR${NC}"
    echo -e "${YELLOW}No backups available to restore${NC}"
    exit 1
fi

# Function to validate backup integrity
validate_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}ERROR: Backup file does not exist: $backup_file${NC}"
        return 1
    fi
    
    # Check file size (should not be empty)
    if [ ! -s "$backup_file" ]; then
        echo -e "${RED}ERROR: Backup file is empty: $backup_file${NC}"
        return 1
    fi
    
    # Check if it's a SQLite database (basic validation)
    if file "$backup_file" | grep -q "SQLite"; then
        echo -e "${GREEN}✓ Backup file appears to be valid SQLite database${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Warning: Backup file may not be a valid SQLite database${NC}"
        read -p "Continue anyway? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            return 1
        fi
    fi
    
    return 0
}

# Function to create pre-rollback backup
create_current_backup() {
    local current_db="$PROJECT_DIR/db.sqlite3"
    local pre_rollback_backup="$BACKUP_DIR/pre-rollback-$(date +%Y%m%d_%H%M%S).db"
    
    if [ -f "$current_db" ]; then
        echo -e "${YELLOW}Creating backup of current database...${NC}"
        cp "$current_db" "$pre_rollback_backup"
        echo -e "${GREEN}✓ Current database backed up to: $pre_rollback_backup${NC}"
    fi
}

# Step 1: List available backups
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Available Backups${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ -n "${1:-}" ]; then
    # Validate provided backup file path to prevent directory traversal
    SELECTED_BACKUP="$1"
    
    # Check for directory traversal attempts
    if [[ "$SELECTED_BACKUP" =~ \.\. ]] || [[ "$SELECTED_BACKUP" =~ ^/ ]]; then
        echo -e "${RED}ERROR: Invalid backup file path (security violation)${NC}"
        exit 1
    fi
    
    # Ensure backup is within backup directory
    if [[ "$SELECTED_BACKUP" != *"$BACKUP_DIR"* ]] && [[ "$SELECTED_BACKUP" != /* ]]; then
        SELECTED_BACKUP="$BACKUP_DIR/$SELECTED_BACKUP"
    fi
    
    # Validate backup file
    if ! validate_backup "$SELECTED_BACKUP"; then
        exit 1
    fi
else
    # No backup file specified, show list
    echo -e "${YELLOW}Available database backups:${NC}"
    echo ""
    
    BACKUPS=($(ls -t "$BACKUP_DIR"/db.sqlite3.backup_* 2>/dev/null))
    
    if [ ${#BACKUPS[@]} -eq 0 ]; then
        echo -e "${RED}No backups found!${NC}"
        exit 1
    fi
    
    # Display backups with numbers
    counter=1
    for backup in "${BACKUPS[@]}"; do
        backup_name=$(basename "$backup")
        backup_date=$(echo "$backup_name" | sed 's/db.sqlite3.backup_//' | sed 's/_/ /')
        backup_size=$(du -h "$backup" | cut -f1)
        backup_time=$(stat -c %y "$backup" | cut -d. -f1)
        
        echo -e "${CYAN}[$counter]${NC} $backup_name"
        echo -e "    Date: $backup_date"
        echo -e "    Size: $backup_size"
        echo -e "    Time: $backup_time"
        echo ""
        ((counter++))
    done
    
    # Prompt user to select
    echo -e "${YELLOW}Enter backup number to restore (1-${#BACKUPS[@]}) or 'q' to quit:${NC}"
    read -p "> " selection
    
    if [ "$selection" = "q" ] || [ "$selection" = "Q" ]; then
        echo -e "${YELLOW}Rollback cancelled${NC}"
        exit 0
    fi
    
    # Validate selection
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#BACKUPS[@]} ]; then
        echo -e "${RED}Invalid selection${NC}"
        exit 1
    fi
    
    # Get selected backup
    BACKUP_FILE="${BACKUPS[$((selection-1))]}"
else
    # Backup file specified as argument
    if [ -f "$1" ]; then
        BACKUP_FILE="$1"
    elif [ -f "$BACKUP_DIR/$1" ]; then
        BACKUP_FILE="$BACKUP_DIR/$1"
    else
        echo -e "${RED}ERROR: Backup file not found: $1${NC}"
        exit 1
    fi
fi

# Step 2: Confirm rollback
print_section "Step 2: Confirm Rollback"

echo -e "${YELLOW}You are about to restore from:${NC}"
echo -e "${CYAN}  File: $(basename "$BACKUP_FILE")${NC}"
echo -e "${CYAN}  Size: $(du -h "$BACKUP_FILE" | cut -f1)${NC}"
echo -e "${CYAN}  Date: $(stat -c %y "$BACKUP_FILE" | cut -d. -f1)${NC}"
echo ""
echo -e "${RED}⚠  This will replace the current database!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo -e "${YELLOW}Rollback cancelled${NC}"
    exit 0
fi

# Step 3: Backup current state (before rollback)
print_section "Step 3: Backing Up Current State"

if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    PREROLLBACK_BACKUP="$BACKUP_DIR/db.sqlite3.pre-rollback_${TIMESTAMP}"
    echo -e "${YELLOW}Creating safety backup before rollback...${NC}"
    cp "$PROJECT_DIR/db.sqlite3" "$PREROLLBACK_BACKUP"
    check_success "Current database backed up"
    echo -e "${CYAN}Safety backup: $(basename "$PREROLLBACK_BACKUP")${NC}"
else
    echo -e "${YELLOW}No current database found${NC}"
fi

# Step 4: Stop services
print_section "Step 4: Stopping Services"

echo -e "${YELLOW}Stopping $SERVICE_NAME...${NC}"
systemctl stop $SERVICE_NAME
check_success "Service stopped"

# Step 5: Restore backup
print_section "Step 5: Restoring Backup"

echo -e "${YELLOW}Restoring database from backup...${NC}"
cp "$BACKUP_FILE" "$PROJECT_DIR/db.sqlite3"
check_success "Database restored"

# Set proper permissions
echo -e "${YELLOW}Setting file permissions...${NC}"
chown www-data:www-data "$PROJECT_DIR/db.sqlite3"
chmod 664 "$PROJECT_DIR/db.sqlite3"
check_success "Permissions set"

# Step 6: Run migrations (in case of schema changes)
print_section "Step 6: Applying Migrations"

echo -e "${YELLOW}Running Django migrations...${NC}"
cd "$PROJECT_DIR"
source .venv/bin/activate
python manage.py migrate --no-input
check_success "Migrations applied"

# Step 7: Restart services
print_section "Step 7: Restarting Services"

echo -e "${YELLOW}Starting $SERVICE_NAME...${NC}"
systemctl start $SERVICE_NAME
check_success "Service started"

sleep 2

# Check if service is running
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi

# Step 8: Verify rollback
print_section "Step 8: Verifying Rollback"

echo -e "${YELLOW}Testing HTTP endpoint...${NC}"
sleep 3
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
    echo -e "${GREEN}✓ Application responding (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "${RED}✗ Application not responding (HTTP $HTTP_STATUS)${NC}"
    echo -e "${YELLOW}You may need to check the logs manually${NC}"
fi

# Step 9: Summary
print_section "Rollback Complete"

echo -e "${GREEN}✓ Database successfully restored from backup${NC}"
echo -e "${CYAN}  Restored from: $(basename "$BACKUP_FILE")${NC}"
if [ -n "$PREROLLBACK_BACKUP" ]; then
    echo -e "${CYAN}  Safety backup: $(basename "$PREROLLBACK_BACKUP")${NC}"
fi
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify application functionality in browser"
echo "  2. Check logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  3. Run health check: sudo bash deployment/health-check.sh"
echo ""

# Run health check if available
if [ -f "$PROJECT_DIR/deployment/health-check.sh" ]; then
    echo -e "${YELLOW}Running health check...${NC}"
    bash "$PROJECT_DIR/deployment/health-check.sh"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ ROLLBACK COMPLETED SUCCESSFULLY             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

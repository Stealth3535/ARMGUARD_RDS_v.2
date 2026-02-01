#!/bin/bash
################################################################################
# ArmGuard Secure Backup Script
# 
# Provides encrypted, compressed, and verified backups for production environments
################################################################################

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Load colors
source "$SCRIPT_DIR/colors.sh" 2>/dev/null || {
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
}

# Backup functions
create_secure_backup() {
    local backup_type="$1"  # database, media, full
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="${backup_type}_backup_${timestamp}"
    
    echo -e "${CYAN}Creating secure backup: $backup_name${NC}"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    case "$backup_type" in
        "database")
            backup_database "$backup_name"
            ;;
        "media")
            backup_media "$backup_name"
            ;;
        "full")
            backup_full_system "$backup_name"
            ;;
        *)
            echo -e "${RED}Error: Unknown backup type: $backup_type${NC}"
            exit 1
            ;;
    esac
}

backup_database() {
    local backup_name="$1"
    local temp_file="/tmp/${backup_name}.sql"
    local final_file="${BACKUP_DIR}/${backup_name}.sql.enc"
    
    echo "  → Creating database backup..."
    
    # Create database backup
    if [ -f "$DB_FILE" ]; then
        cp "$DB_FILE" "$temp_file"
    else
        echo -e "${RED}Error: Database file not found: $DB_FILE${NC}"
        return 1
    fi
    
    # Compress if enabled
    if [ "$BACKUP_COMPRESSION" = "yes" ]; then
        echo "  → Compressing backup..."
        gzip "$temp_file"
        temp_file="${temp_file}.gz"
    fi
    
    # Encrypt if enabled
    if [ "$BACKUP_ENCRYPTION" = "yes" ]; then
        echo "  → Encrypting backup..."
        if [ ! -f "$BACKUP_PASSWORD_FILE" ]; then
            echo "  → Generating backup encryption key..."
            openssl rand -base64 32 > "$BACKUP_PASSWORD_FILE"
            chmod 600 "$BACKUP_PASSWORD_FILE"
        fi
        
        openssl enc -aes-256-cbc -salt -pbkdf2 \
            -in "$temp_file" \
            -out "$final_file" \
            -pass "file:$BACKUP_PASSWORD_FILE"
        
        # Clean up temp file
        rm "$temp_file"
    else
        mv "$temp_file" "$final_file"
    fi
    
    # Verify backup integrity
    if [ "$BACKUP_VERIFICATION" = "yes" ]; then
        verify_backup "$final_file"
    fi
    
    echo -e "${GREEN}  ✓ Database backup created: $final_file${NC}"
}

backup_media() {
    local backup_name="$1"
    local temp_file="/tmp/${backup_name}.tar"
    local final_file="${BACKUP_DIR}/${backup_name}.tar.enc"
    
    echo "  → Creating media backup..."
    
    # Create media backup
    if [ -d "$MEDIA_DIR" ] && [ "$(ls -A $MEDIA_DIR)" ]; then
        tar -cf "$temp_file" -C "$(dirname $MEDIA_DIR)" "$(basename $MEDIA_DIR)"
    else
        echo "  → No media files to backup"
        return 0
    fi
    
    # Compress if enabled
    if [ "$BACKUP_COMPRESSION" = "yes" ]; then
        echo "  → Compressing media backup..."
        gzip "$temp_file"
        temp_file="${temp_file}.gz"
    fi
    
    # Encrypt if enabled
    if [ "$BACKUP_ENCRYPTION" = "yes" ]; then
        echo "  → Encrypting media backup..."
        openssl enc -aes-256-cbc -salt -pbkdf2 \
            -in "$temp_file" \
            -out "$final_file" \
            -pass "file:$BACKUP_PASSWORD_FILE"
        rm "$temp_file"
    else
        mv "$temp_file" "$final_file"
    fi
    
    echo -e "${GREEN}  ✓ Media backup created: $final_file${NC}"
}

backup_full_system() {
    local backup_name="$1"
    
    echo "  → Creating full system backup..."
    backup_database "db_${backup_name}"
    backup_media "media_${backup_name}"
    
    echo -e "${GREEN}  ✓ Full system backup completed${NC}"
}

verify_backup() {
    local backup_file="$1"
    
    echo "  → Verifying backup integrity..."
    
    if [ "$BACKUP_ENCRYPTION" = "yes" ]; then
        # Verify encrypted backup can be decrypted
        if openssl enc -aes-256-cbc -d -pbkdf2 \
            -in "$backup_file" \
            -pass "file:$BACKUP_PASSWORD_FILE" \
            -out /dev/null 2>/dev/null; then
            echo -e "${GREEN}    ✓ Backup encryption verified${NC}"
        else
            echo -e "${RED}    ✗ Backup encryption verification failed${NC}"
            return 1
        fi
    fi
    
    # Check file size
    local size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo "0")
    if [ "$size" -gt 1024 ]; then  # At least 1KB
        echo -e "${GREEN}    ✓ Backup size verification passed (${size} bytes)${NC}"
    else
        echo -e "${RED}    ✗ Backup size verification failed (${size} bytes)${NC}"
        return 1
    fi
}

restore_backup() {
    local backup_file="$1"
    local restore_type="$2"  # database, media, full
    
    echo -e "${YELLOW}Restoring backup: $(basename $backup_file)${NC}"
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found: $backup_file${NC}"
        return 1
    fi
    
    # Create safety backup before restore
    echo "  → Creating safety backup before restore..."
    create_secure_backup "database"
    
    # Decrypt backup if needed
    local temp_file="/tmp/restore_$(date +%s)"
    if [[ "$backup_file" == *.enc ]]; then
        echo "  → Decrypting backup..."
        openssl enc -aes-256-cbc -d -pbkdf2 \
            -in "$backup_file" \
            -out "$temp_file" \
            -pass "file:$BACKUP_PASSWORD_FILE"
    else
        cp "$backup_file" "$temp_file"
    fi
    
    # Decompress if needed
    if [[ "$temp_file" == *.gz ]] || [[ "$backup_file" == *.gz ]]; then
        echo "  → Decompressing backup..."
        gunzip "$temp_file" 2>/dev/null || gunzip < "$temp_file" > "${temp_file}.decompressed"
        temp_file="${temp_file}.decompressed"
    fi
    
    # Restore based on type
    case "$restore_type" in
        "database")
            echo "  → Restoring database..."
            cp "$temp_file" "$DB_FILE"
            ;;
        "media")
            echo "  → Restoring media files..."
            tar -xf "$temp_file" -C "$(dirname $MEDIA_DIR)"
            ;;
        *)
            echo -e "${RED}Error: Unknown restore type: $restore_type${NC}"
            rm "$temp_file"
            return 1
            ;;
    esac
    
    # Clean up temp file
    rm "$temp_file"
    
    echo -e "${GREEN}  ✓ Restore completed successfully${NC}"
}

cleanup_old_backups() {
    local retention_days="$1"
    
    echo -e "${CYAN}Cleaning up backups older than $retention_days days...${NC}"
    
    # Find and remove old backups
    local deleted_count=0
    while IFS= read -r -d '' backup_file; do
        rm "$backup_file"
        deleted_count=$((deleted_count + 1))
        echo "  → Deleted: $(basename $backup_file)"
    done < <(find "$BACKUP_DIR" -name "*backup*" -type f -mtime +$retention_days -print0 2>/dev/null)
    
    if [ $deleted_count -eq 0 ]; then
        echo "  → No old backups found"
    else
        echo -e "${GREEN}  ✓ Deleted $deleted_count old backup(s)${NC}"
    fi
}

# Main execution
main() {
    case "${1:-}" in
        "create")
            create_secure_backup "${2:-database}"
            ;;
        "restore")
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: Backup file path required for restore${NC}"
                exit 1
            fi
            restore_backup "$2" "${3:-database}"
            ;;
        "cleanup")
            cleanup_old_backups "${DB_BACKUP_RETENTION}"
            ;;
        "verify")
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: Backup file path required for verification${NC}"
                exit 1
            fi
            verify_backup "$2"
            ;;
        *)
            echo "Usage: $0 {create|restore|cleanup|verify} [options]"
            echo ""
            echo "Commands:"
            echo "  create [type]       Create backup (database|media|full)"
            echo "  restore <file> [type] Restore from backup file"
            echo "  cleanup             Remove old backups"
            echo "  verify <file>       Verify backup integrity"
            echo ""
            echo "Examples:"
            echo "  $0 create database"
            echo "  $0 restore /path/to/backup.enc database"
            echo "  $0 cleanup"
            echo "  $0 verify /path/to/backup.enc"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
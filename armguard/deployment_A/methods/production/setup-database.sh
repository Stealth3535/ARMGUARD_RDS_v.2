#!/bin/bash
################################################################################
# ArmGuard Database Setup Script
# 
# Handles both SQLite and PostgreSQL database configurations
################################################################################

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Load colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# Database setup functions
setup_sqlite() {
    echo -e "${CYAN}Setting up SQLite database...${NC}"
    
    # Ensure database directory exists
    mkdir -p "$(dirname $DB_FILE)"
    
    # Set proper permissions
    touch "$DB_FILE"
    chown $RUN_USER:$RUN_GROUP "$DB_FILE"
    chmod 664 "$DB_FILE"
    
    echo -e "${GREEN}✓ SQLite database configured: $DB_FILE${NC}"
}

setup_postgresql() {
    echo -e "${CYAN}Setting up PostgreSQL database...${NC}"
    
    # Check if PostgreSQL is installed
    if ! command -v psql &> /dev/null; then
        echo -e "${YELLOW}Installing PostgreSQL...${NC}"
        apt-get update
        apt-get install -y postgresql postgresql-contrib libpq-dev
        
        # Start and enable PostgreSQL
        systemctl start postgresql
        systemctl enable postgresql
    fi
    
    # Create database and user
    echo -e "${BLUE}Creating database and user...${NC}"
    
    # Generate password if not provided
    if [ -z "$POSTGRES_PASSWORD" ]; then
        POSTGRES_PASSWORD=$(openssl rand -base64 32)
        echo "Generated PostgreSQL password: $POSTGRES_PASSWORD"
        echo "ARMGUARD_DB_PASSWORD=\"$POSTGRES_PASSWORD\"" >> "${PROJECT_DIR}/.env"
    fi
    
    # Create database and user as postgres user
    sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$POSTGRES_USER') THEN
        CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$POSTGRES_DB')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
EOF
    
    # Configure PostgreSQL for optimal performance
    configure_postgresql_performance
    
    echo -e "${GREEN}✓ PostgreSQL database configured${NC}"
    echo -e "${YELLOW}Database: $POSTGRES_DB${NC}"
    echo -e "${YELLOW}User: $POSTGRES_USER${NC}"
    echo -e "${YELLOW}Host: $POSTGRES_HOST:$POSTGRES_PORT${NC}"
}

configure_postgresql_performance() {
    echo -e "${BLUE}Optimizing PostgreSQL configuration...${NC}"
    
    # Get PostgreSQL version and config file location
    PG_VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | head -n 1 | sed 's/.*PostgreSQL \([0-9]\+\).*/\1/')
    PG_CONFIG="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    
    if [ -f "$PG_CONFIG" ]; then
        # Backup original config
        cp "$PG_CONFIG" "$PG_CONFIG.backup"
        
        # Apply optimizations
        cat >> "$PG_CONFIG" <<EOF

# ArmGuard Performance Optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB

# Connection settings
max_connections = $(($DB_CONN_POOL_SIZE + 50))

# Logging
log_statement = 'mod'
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
EOF
        
        # Restart PostgreSQL to apply changes
        systemctl restart postgresql
        
        echo -e "${GREEN}✓ PostgreSQL performance optimizations applied${NC}"
    fi
}

create_database_backup() {
    case "$DB_ENGINE" in
        "sqlite")
            backup_sqlite
            ;;
        "postgresql")
            backup_postgresql
            ;;
        *)
            echo -e "${RED}Error: Unknown database engine: $DB_ENGINE${NC}"
            exit 1
            ;;
    esac
}

backup_sqlite() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/db.sqlite3.backup_$timestamp"
    
    echo -e "${CYAN}Creating SQLite backup...${NC}"
    mkdir -p "$BACKUP_DIR"
    
    cp "$DB_FILE" "$backup_file"
    echo -e "${GREEN}✓ SQLite backup created: $backup_file${NC}"
}

backup_postgresql() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/postgres_backup_$timestamp.sql"
    
    echo -e "${CYAN}Creating PostgreSQL backup...${NC}"
    mkdir -p "$BACKUP_DIR"
    
    # Create backup using pg_dump
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean --create --if-exists \
        > "$backup_file"
    
    echo -e "${GREEN}✓ PostgreSQL backup created: $backup_file${NC}"
}

test_database_connection() {
    echo -e "${CYAN}Testing database connection...${NC}"
    
    case "$DB_ENGINE" in
        "sqlite")
            if [ -f "$DB_FILE" ] && [ -r "$DB_FILE" ] && [ -w "$DB_FILE" ]; then
                echo -e "${GREEN}✓ SQLite database accessible${NC}"
                return 0
            else
                echo -e "${RED}✗ SQLite database not accessible${NC}"
                return 1
            fi
            ;;
        "postgresql")
            if PGPASSWORD="$POSTGRES_PASSWORD" psql \
                -h "$POSTGRES_HOST" \
                -p "$POSTGRES_PORT" \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                -c "SELECT 1;" > /dev/null 2>&1; then
                echo -e "${GREEN}✓ PostgreSQL connection successful${NC}"
                return 0
            else
                echo -e "${RED}✗ PostgreSQL connection failed${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${RED}Error: Unknown database engine: $DB_ENGINE${NC}"
            return 1
            ;;
    esac
}

# Main execution
main() {
    case "${1:-}" in
        "setup")
            case "$DB_ENGINE" in
                "sqlite")
                    setup_sqlite
                    ;;
                "postgresql")
                    setup_postgresql
                    ;;
                *)
                    echo -e "${RED}Error: Unknown database engine: $DB_ENGINE${NC}"
                    echo "Supported engines: sqlite, postgresql"
                    exit 1
                    ;;
            esac
            ;;
        "backup")
            create_database_backup
            ;;
        "test")
            test_database_connection
            ;;
        "optimize")
            if [ "$DB_ENGINE" = "postgresql" ]; then
                configure_postgresql_performance
            else
                echo -e "${YELLOW}Optimization only available for PostgreSQL${NC}"
            fi
            ;;
        *)
            echo "Usage: $0 {setup|backup|test|optimize}"
            echo ""
            echo "Commands:"
            echo "  setup    Setup database (SQLite or PostgreSQL)"
            echo "  backup   Create database backup"
            echo "  test     Test database connection"
            echo "  optimize Configure PostgreSQL for optimal performance"
            echo ""
            echo "Environment Variables:"
            echo "  ARMGUARD_DB_ENGINE    Database engine (sqlite|postgresql)"
            echo "  ARMGUARD_DB_NAME      PostgreSQL database name"
            echo "  ARMGUARD_DB_USER      PostgreSQL username"
            echo "  ARMGUARD_DB_PASSWORD  PostgreSQL password"
            echo "  ARMGUARD_DB_HOST      PostgreSQL host"
            echo "  ARMGUARD_DB_PORT      PostgreSQL port"
            exit 1
            ;;
    esac
}

main "$@"
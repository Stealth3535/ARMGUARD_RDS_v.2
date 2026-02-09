# =============================================================================
# ARMGUARD SYSTEMATIZED DEPLOYMENT CONFIGURATION
# =============================================================================
# This configuration unifies all deployment methods into one systematized approach
# Version: 4.0.0
# =============================================================================

# Project Configuration
PROJECT_NAME="armguard"
PROJECT_DISPLAY_NAME="ArmGuard Military Armory Management"
PROJECT_VERSION="2.0.0"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ARMGUARD_ROOT="$PROJECT_ROOT/armguard"

# System Paths
DEPLOYMENT_ROOT="$PROJECT_ROOT/armguard/deployment"
UNIFIED_COMPONENTS_ROOT="$PROJECT_ROOT/deployment"
LOG_DIR="/var/log/armguard-deploy"
BACKUP_DIR="/opt/armguard-backup"

# Network Configuration (Systematized)
declare -A NETWORK_CONFIG=(
    ["lan_port"]="8443"
    ["wan_port"]="443" 
    ["ssh_port"]="22"
    ["vpn_port"]="51820"
    ["redis_port"]="6379"
    ["development_port"]="8000"
)

# Security Configuration
declare -A SECURITY_CONFIG=(
    ["ssl_cert_dir"]="/etc/ssl/armguard"
    ["firewall_enabled"]="true"
    ["fail2ban_enabled"]="true"
    ["rate_limiting"]="true"
)

# Database Configuration (Systematized)
declare -A DATABASE_CONFIG=(
    ["development"]="sqlite3"
    ["production"]="postgresql"
    ["testing"]="postgresql"
    ["db_name"]="armguard_db"
    ["db_user"]="armguard_user"
)

# Service Configuration
declare -A SERVICES_CONFIG=(
    ["webserver"]="nginx"
    ["app_server"]="gunicorn"
    ["websocket_server"]="daphne"
    ["cache_server"]="redis"
    ["monitoring"]="prometheus"  
)

# =============================================================================
# SYSTEMATIZED DEPLOYMENT METHODS INTEGRATION
# =============================================================================

# Integration paths to existing deployment methods
METHODS_DIR="$DEPLOYMENT_ROOT/methods"
PRODUCTION_METHOD="$METHODS_DIR/production"
DOCKER_METHOD="$METHODS_DIR/docker-testing"  
VMWARE_METHOD="$METHODS_DIR/vmware-setup"
BASIC_METHOD="$METHODS_DIR/basic-setup"

# Unified components integration
UNIFIED_REDIS_MANAGER="$UNIFIED_COMPONENTS_ROOT/unified-redis-manager.sh"
UNIFIED_SSL_MANAGER="$UNIFIED_COMPONENTS_ROOT/unified-ssl-port-manager.sh" 
UNIFIED_CLEANUP="$UNIFIED_COMPONENTS_ROOT/unified-system-cleanup.sh"

# =============================================================================
# SYSTEMATIZED FUNCTIONS LIBRARY
# =============================================================================

# Check if unified components are available
check_unified_components() {
    local components_available=true
    
    if [ ! -f "$UNIFIED_REDIS_MANAGER" ]; then
        log_warn "Unified Redis manager not found, using integrated Redis setup"
        components_available=false
    fi
    
    if [ ! -f "$UNIFIED_SSL_MANAGER" ]; then
        log_warn "Unified SSL manager not found, using basic SSL setup"
        components_available=false
    fi
    
    if [ ! -f "$UNIFIED_CLEANUP" ]; then
        log_warn "Unified cleanup not found, using basic cleanup"
        components_available=false
    fi
    
    return $components_available
}

# Systematized Redis setup (integrates both approaches)
systematized_redis_setup() {
    local approach="$1"
    
    echo -e "${CYAN}🔧 Systematized Redis Setup${NC}"
    
    if [ -f "$UNIFIED_REDIS_MANAGER" ]; then
        echo -e "${GREEN}  ├─ Using unified Redis manager${NC}"
        bash "$UNIFIED_REDIS_MANAGER" --approach "$approach"
    else
        echo -e "${YELLOW}  ├─ Using integrated Redis setup${NC}"
        setup_redis "all"  # From master-config.sh
    fi
    
    # Verify Redis is working
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}  └─ ✅ Redis setup successful${NC}"
        return 0
    else
        echo -e "${RED}  └─ ❌ Redis setup failed${NC}"
        return 1
    fi
}

# Systematized SSL setup (integrates certificate management)
systematized_ssl_setup() {
    local ssl_type="$1"
    
    echo -e "${CYAN}🔐 Systematized SSL Setup${NC}"
    
    if [ -f "$UNIFIED_SSL_MANAGER" ]; then
        echo -e "${GREEN}  ├─ Using unified SSL manager${NC}"
        bash "$UNIFIED_SSL_MANAGER" --type "$ssl_type"
    else
        echo -e "${YELLOW}  ├─ Using basic SSL setup${NC}"
        case "$ssl_type" in
            "development"|"self-signed")
                generate_self_signed_cert
                ;;
            "production"|"letsencrypt")
                install_letsencrypt_cert
                ;;
            *)
                generate_self_signed_cert
                ;;
        esac
    fi
    
    echo -e "${GREEN}  └─ SSL configuration completed${NC}"
}

# Systematized system cleanup (resolves conflicts)
systematized_cleanup() {
    echo -e "${CYAN}🧹 Systematized System Cleanup${NC}"
    
    if [ -f "$UNIFIED_CLEANUP" ]; then
        echo -e "${GREEN}  ├─ Using unified cleanup system${NC}"
        bash "$UNIFIED_CLEANUP" --comprehensive
    else
        echo -e "${YELLOW}  ├─ Using basic cleanup${NC}"
        
        # Basic cleanup operations
        echo -e "${CYAN}  ├─ Stopping conflicting services...${NC}"
        systemctl stop nginx 2>/dev/null || true
        systemctl stop armguard 2>/dev/null || true
        
        echo -e "${CYAN}  ├─ Cleaning temporary files...${NC}"
        rm -rf /tmp/armguard-* 2>/dev/null || true
        
        echo -e "${CYAN}  └─ Basic cleanup completed${NC}"
    fi
}

# Systematized deployment method selector
systematized_execute_method() {
    local method="$1"
    local method_args="${@:2}"
    
    case "$method" in
        "production-full")
            if [ -d "$PRODUCTION_METHOD" ]; then
                cd "$PRODUCTION_METHOD"
                bash master-deploy.sh $method_args
            else
                echo -e "${RED}❌ Production method not available${NC}"
                return 1
            fi
            ;;
        "testing-docker")
            if [ -d "$DOCKER_METHOD" ]; then
                cd "$DOCKER_METHOD" 
                bash run_all_tests.sh $method_args
            else
                echo -e "${RED}❌ Docker testing method not available${NC}"
                return 1
            fi
            ;;
        "vm-development")
            if [ -d "$VMWARE_METHOD" ]; then
                cd "$VMWARE_METHOD"
                bash vm-deploy.sh $method_args
            else
                echo -e "${RED}❌ VMware method not available${NC}"
                return 1
            fi
            ;;
        "production-basic")
            if [ -d "$BASIC_METHOD" ]; then
                cd "$BASIC_METHOD"
                bash serversetup.sh $method_args
            else
                echo -e "${RED}❌ Basic setup method not available${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${RED}❌ Unknown method: $method${NC}"
            return 1
            ;;
    esac
}

# =============================================================================
# SYSTEMATIZED VALIDATION FUNCTIONS
# =============================================================================

validate_systematized_deployment() {
    echo -e "${CYAN}🔍 Systematized Deployment Validation${NC}"
    local validation_passed=true
    
    # Check Django application
    if [ -f "$ARMGUARD_ROOT/manage.py" ]; then
        echo -e "${GREEN}  ✅ Django application found${NC}"
    else
        echo -e "${RED}  ❌ Django application not found${NC}"
        validation_passed=false
    fi
    
    # Check Redis  
    if systemctl is-active --quiet redis-server 2>/dev/null || systemctl is-active --quiet redis 2>/dev/null; then
        echo -e "${GREEN}  ✅ Redis service running${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Redis not running (will be configured)${NC}"
    fi
    
    # Check available deployment methods
    local methods_count=0
    for method_dir in "$PRODUCTION_METHOD" "$DOCKER_METHOD" "$VMWARE_METHOD" "$BASIC_METHOD"; do
        if [ -d "$method_dir" ]; then
            ((methods_count++))
        fi
    done
    echo -e "${GREEN}  ✅ Available deployment methods: $methods_count${NC}"
    
    # Check unified components
    if check_unified_components; then
        echo -e "${GREEN}  ✅ Unified components available${NC}"
    else
        echo -e "${YELLOW}  ⚠️  Some unified components missing (will use fallbacks)${NC}"
    fi
    
    if [ "$validation_passed" = true ]; then
        echo -e "${GREEN}  └─ ✅ System validation passed${NC}"
        return 0
    else
        echo -e "${RED}  └─ ❌ System validation failed${NC}"
        return 1
    fi
}

# =============================================================================
# GLOBAL CONFIGURATION EXPORT
# =============================================================================

# Make configurations available to deployment scripts
export PROJECT_NAME PROJECT_DISPLAY_NAME PROJECT_VERSION PROJECT_ROOT ARMGUARD_ROOT
export DEPLOYMENT_ROOT UNIFIED_COMPONENTS_ROOT LOG_DIR BACKUP_DIR
export METHODS_DIR PRODUCTION_METHOD DOCKER_METHOD VMWARE_METHOD BASIC_METHOD  
export UNIFIED_REDIS_MANAGER UNIFIED_SSL_MANAGER UNIFIED_CLEANUP

# Export systematized functions
export -f systematized_redis_setup systematized_ssl_setup systematized_cleanup
export -f systematized_execute_method validate_systematized_deployment
export -f check_unified_components
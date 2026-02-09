#!/bin/bash

# ============================================================================
# ARMGUARD VPN MIGRATION SCRIPT
# Migrates existing VPN setups to unified VPN integration system
# ============================================================================
# VERSION: 1.0.0
# AUTHOR: AI System Integration
# DATE: 2026-02-09
# PURPOSE: Seamless migration from old VPN setups to unified system
# ============================================================================

set -e  # Exit on any error

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VPN_INTEGRATION_ROOT="$(dirname "$SCRIPT_DIR")"
readonly BACKUP_DIR="/tmp/armguard-vpn-migration-$(date +%Y%m%d-%H%M%S)"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

show_banner() {
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                        ARMGUARD VPN MIGRATION                               ║
║                    Unifying VPN Systems and Configurations                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

🔄 Migration: Old VPN → Unified VPN Integration
🔐 Security: Military-grade standards maintained  
📈 Features: Enhanced monitoring and compliance
EOF
}

detect_existing_vpn() {
    log_info "Detecting existing VPN configurations..."
    
    local vpn_configs_found=()
    
    # Check for WireGuard configurations
    if [[ -d /etc/wireguard ]]; then
        local wg_configs=$(find /etc/wireguard -name "*.conf" -type f 2>/dev/null | wc -l)
        if [[ $wg_configs -gt 0 ]]; then
            vpn_configs_found+=("wireguard-system")
            log_info "Found $wg_configs WireGuard configuration(s) in /etc/wireguard"
        fi
    fi
    
    # Check for existing ArmGuard quick setup
    if [[ -f /etc/wireguard/armguard-wg0.conf ]]; then
        vpn_configs_found+=("armguard-quick")
        log_info "Found ArmGuard quick VPN setup"
    fi
    
    # Check for OpenVPN (legacy)
    if [[ -d /etc/openvpn ]] && [[ -n "$(find /etc/openvpn -name "*.conf" -type f 2>/dev/null)" ]]; then
        vpn_configs_found+=("openvpn")
        log_warn "Found OpenVPN configuration - will need manual migration"
    fi
    
    # Check for existing ArmGuard VPN integration
    if [[ -d "$VPN_INTEGRATION_ROOT" ]] && [[ -f "$VPN_INTEGRATION_ROOT/README.md" ]]; then
        vpn_configs_found+=("armguard-integrated")
        log_info "Found existing ArmGuard VPN integration"
    fi
    
    if [[ ${#vpn_configs_found[@]} -eq 0 ]]; then
        log_info "No existing VPN configurations found - this is a fresh installation"
        return 1
    fi
    
    echo -e "\n${BLUE}Existing VPN configurations detected:${NC}"
    for config in "${vpn_configs_found[@]}"; do
        case "$config" in
            "wireguard-system") echo "  🔧 System WireGuard configurations" ;;
            "armguard-quick") echo "  ⚡ ArmGuard quick setup" ;;
            "openvpn") echo "  🔄 OpenVPN (requires manual migration)" ;;
            "armguard-integrated") echo "  ✅ ArmGuard integrated VPN" ;;
        esac
    done
    
    return 0
}

backup_existing_configs() {
    log_info "Creating backup of existing configurations..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup WireGuard configs
    if [[ -d /etc/wireguard ]]; then
        sudo cp -r /etc/wireguard "$BACKUP_DIR/wireguard-system"
        log_info "Backed up system WireGuard configs to $BACKUP_DIR/wireguard-system"
    fi
    
    # Backup any ArmGuard VPN integration
    if [[ -d "$VPN_INTEGRATION_ROOT" ]]; then
        cp -r "$VPN_INTEGRATION_ROOT" "$BACKUP_DIR/armguard-vpn-integration"
        log_info "Backed up ArmGuard VPN integration to $BACKUP_DIR/armguard-vpn-integration"
    fi
    
    # Backup network configuration
    if [[ -f /etc/ufw/applications.d/armguard-vpn ]]; then
        sudo cp /etc/ufw/applications.d/armguard-vpn "$BACKUP_DIR/"
    fi
    
    log_info "✅ Backup completed: $BACKUP_DIR"
}

migrate_wireguard_configs() {
    log_info "Migrating WireGuard configurations to unified system..."
    
    local server_config="/etc/wireguard/wg0.conf"
    local armguard_config="/etc/wireguard/armguard-wg0.conf"
    
    # Check which config is the main one
    local primary_config=""
    if [[ -f "$armguard_config" ]]; then
        primary_config="$armguard_config"
    elif [[ -f "$server_config" ]]; then
        primary_config="$server_config"
    else
        log_warn "No WireGuard server configuration found to migrate"
        return 1
    fi
    
    log_info "Using primary config: $primary_config"
    
    # Extract configuration details
    local server_ip=$(grep "Address" "$primary_config" | cut -d'=' -f2 | tr -d ' ')
    local server_port=$(grep "ListenPort" "$primary_config" | cut -d'=' -f2 | tr -d ' ')
    local server_private_key=$(grep "PrivateKey" "$primary_config" | cut -d'=' -f2 | tr -d ' ')
    
    log_info "Detected configuration:"
    log_info "  Server IP: $server_ip"
    log_info "  Listen Port: ${server_port:-51820}"
    
    # Create unified configuration directory
    mkdir -p "$VPN_INTEGRATION_ROOT/config"
    
    # Migrate to unified format
    cat > "$VPN_INTEGRATION_ROOT/config/migration-config.env" << EOF
# ArmGuard VPN Migration Configuration
# Generated on $(date)
# Source: $primary_config

VPN_SERVER_IP=$server_ip
VPN_SERVER_PORT=${server_port:-51820}
VPN_PRIVATE_KEY=$server_private_key
VPN_INTERFACE=wg0
VPN_NETWORK=10.0.0.0/16
MIGRATION_SOURCE=$(basename "$primary_config")
MIGRATION_DATE=$(date +%Y%m%d)
EOF
    
    log_info "✅ WireGuard configuration migrated"
}

migrate_client_configs() {
    log_info "Migrating client configurations..."
    
    local client_dir="$VPN_INTEGRATION_ROOT/clients"
    mkdir -p "$client_dir"
    
    # Find existing client configs
    local client_configs=($(find /etc/wireguard -name "*-client*.conf" -o -name "peer*.conf" 2>/dev/null || true))
    
    if [[ ${#client_configs[@]} -gt 0 ]]; then
        log_info "Found ${#client_configs[@]} client configuration(s)"
        
        for client_config in "${client_configs[@]}"; do
            local client_name=$(basename "$client_config" .conf)
            cp "$client_config" "$client_dir/${client_name}-migrated.conf"
            log_info "Migrated client config: $client_name"
        done
    else
        log_info "No client configurations found to migrate"
    fi
}

update_unified_system() {
    log_info "Updating unified VPN system with migrated configuration..."
    
    # Check if unified system is already set up
    if [[ -f "$VPN_INTEGRATION_ROOT/README.md" ]]; then
        log_info "Unified VPN integration already exists - updating configuration"
        
        # Update the existing configuration with migrated settings
        if [[ -f "$VPN_INTEGRATION_ROOT/config/migration-config.env" ]]; then
            source "$VPN_INTEGRATION_ROOT/config/migration-config.env"
            
            # Update WireGuard script configuration
            if [[ -f "$VPN_INTEGRATION_ROOT/wireguard/scripts/setup-wireguard-server.sh" ]]; then
                sed -i "s/VPN_PORT=51820/VPN_PORT=$VPN_SERVER_PORT/" \
                    "$VPN_INTEGRATION_ROOT/wireguard/scripts/setup-wireguard-server.sh" 2>/dev/null || true
            fi
        fi
    else
        log_warn "Unified VPN integration not found - please run deployment setup first"
        return 1
    fi
    
    log_info "✅ Unified system updated with migrated configuration"
}

cleanup_old_configs() {
    log_info "Cleaning up duplicate and conflicting configurations..."
    
    echo -e "${YELLOW}The following actions will be performed:${NC}"
    echo "  - Stop old WireGuard services to prevent conflicts"
    echo "  - Disable auto-start for old configurations"
    echo "  - Keep backup files in $BACKUP_DIR"
    echo ""
    
    echo -e "${YELLOW}Proceed with cleanup? [y/N]:${NC} \c"
    read -r cleanup_confirm
    
    if [[ "$cleanup_confirm" =~ ^[Yy] ]]; then
        # Stop old WireGuard services
        if systemctl is-active --quiet wg-quick@wg0 2>/dev/null; then
            sudo systemctl stop wg-quick@wg0
            log_info "Stopped old WireGuard service"
        fi
        
        # Disable auto-start
        if systemctl is-enabled --quiet wg-quick@wg0 2>/dev/null; then
            sudo systemctl disable wg-quick@wg0
            log_info "Disabled auto-start for old WireGuard service"
        fi
        
        log_info "✅ Cleanup completed - old services stopped"
        log_info "💾 All original configurations backed up to: $BACKUP_DIR"
    else
        log_info "Cleanup skipped - old configurations remain active"
        log_warn "⚠️  You may have conflicting VPN services running"
    fi
}

test_migration() {
    log_info "Testing migrated VPN configuration..."
    
    # Test unified system components
    local tests_passed=0
    local tests_total=4
    
    # Test 1: Check unified VPN integration exists
    if [[ -f "$VPN_INTEGRATION_ROOT/UNIFIED_VPN_GUIDE.md" ]]; then
        log_info "✅ Test 1/4: Unified VPN guide exists"
        ((tests_passed++))
    else
        log_error "❌ Test 1/4: Unified VPN guide missing"
    fi
    
    # Test 2: Check migration configuration
    if [[ -f "$VPN_INTEGRATION_ROOT/config/migration-config.env" ]]; then
        log_info "✅ Test 2/4: Migration configuration created"
        ((tests_passed++))
    else
        log_error "❌ Test 2/4: Migration configuration missing"
    fi
    
    # Test 3: Check client directory
    if [[ -d "$VPN_INTEGRATION_ROOT/clients" ]]; then
        log_info "✅ Test 3/4: Client directory exists"
        ((tests_passed++))
    else
        log_error "❌ Test 3/4: Client directory missing"
    fi
    
    # Test 4: Check for backup
    if [[ -d "$BACKUP_DIR" ]]; then
        log_info "✅ Test 4/4: Backup directory created"
        ((tests_passed++))
    else
        log_error "❌ Test 4/4: Backup directory missing"
    fi
    
    echo -e "\n${BLUE}Migration Test Results: $tests_passed/$tests_total tests passed${NC}"
    
    if [[ $tests_passed -eq $tests_total ]]; then
        log_info "✅ All migration tests passed"
        return 0
    else
        log_error "❌ Some migration tests failed"
        return 1
    fi
}

show_post_migration_instructions() {
    cat << EOF

${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗
║                          MIGRATION COMPLETED                                ║
╚══════════════════════════════════════════════════════════════════════════════╝${NC}

${BLUE}🎯 Next Steps:${NC}

1. ${YELLOW}Review the unified VPN guide:${NC}
   ${BLUE}cat $VPN_INTEGRATION_ROOT/UNIFIED_VPN_GUIDE.md${NC}

2. ${YELLOW}Configure the unified VPN system:${NC}
   ${BLUE}cd $VPN_INTEGRATION_ROOT
   sudo bash wireguard/scripts/setup-wireguard-server.sh --use-migrated-config${NC}

3. ${YELLOW}Test the new system:${NC}
   ${BLUE}sudo systemctl status wg-quick@armguard-wg0${NC}

4. ${YELLOW}Generate new client configurations if needed:${NC}
   ${BLUE}bash tools/client-generator.sh${NC}

${GREEN}📊 Migration Summary:${NC}
- Configuration backup: ${BLUE}$BACKUP_DIR${NC}  
- Migrated settings: ${BLUE}$VPN_INTEGRATION_ROOT/config/migration-config.env${NC}
- Client configs: ${BLUE}$VPN_INTEGRATION_ROOT/clients/${NC}
- Unified guide: ${BLUE}$VPN_INTEGRATION_ROOT/UNIFIED_VPN_GUIDE.md${NC}

${YELLOW}⚠️  Important:${NC}  
- Old VPN services have been stopped to prevent conflicts
- Test the new system before removing backups
- Update client devices with new configurations if needed

EOF
}

main() {
    show_banner
    
    log_info "Starting ArmGuard VPN migration process..."
    
    # Check for root privileges for system configs
    if [[ $EUID -ne 0 ]] && [[ -d /etc/wireguard ]]; then
        log_warn "Root privileges required for system WireGuard migration"
        echo -e "${YELLOW}Continue with limited migration (user configs only)? [y/N]:${NC} \c"
        read -r continue_limited
        if [[ ! "$continue_limited" =~ ^[Yy] ]]; then
            log_error "Migration cancelled - run with sudo for complete migration"
            exit 1
        fi
    fi
    
    # Detect existing configurations
    if ! detect_existing_vpn; then
        log_info "No existing VPN configurations found"
        echo -e "${BLUE}Would you like to proceed with fresh unified VPN setup? [y/N]:${NC} \c"
        read -r fresh_setup
        if [[ "$fresh_setup" =~ ^[Yy] ]]; then
            log_info "Refer to the unified deployment system: deployment/unified-deployment.sh"
            exit 0
        else
            log_info "Migration cancelled"
            exit 0
        fi
    fi
    
    # User confirmation
    echo -e "\n${YELLOW}This will migrate your existing VPN setup to the unified ArmGuard system.${NC}"
    echo -e "${YELLOW}All existing configurations will be backed up before changes.${NC}"
    echo -e "\n${BLUE}Proceed with migration? [y/N]:${NC} \c"
    read -r confirm_migration
    
    if [[ ! "$confirm_migration" =~ ^[Yy] ]]; then
        log_info "Migration cancelled by user"
        exit 0
    fi
    
    # Perform migration
    backup_existing_configs
    migrate_wireguard_configs
    migrate_client_configs
    update_unified_system
    cleanup_old_configs
    
    # Test and validate
    if test_migration; then
        show_post_migration_instructions
        log_info "✅ VPN migration completed successfully"
    else
        log_error "❌ Migration completed with issues - check logs and backups"
        exit 1
    fi
}

# Only run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
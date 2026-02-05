#!/bin/bash
################################################################################
# ArmGuard Secrets Management Script
# 
# Handles secure storage and retrieval of sensitive configuration data
# Supports multiple backends: file-based, HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
################################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Trap for cleanup
cleanup() {
    # Remove any temporary files
    rm -f /tmp/secrets_temp.* 2>/dev/null || true
    
    # Clear sensitive variables
    unset DB_PASSWORD DJANGO_SECRET_KEY VAULT_TOKEN 2>/dev/null || true
}
trap cleanup EXIT

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# Secret keys that should be managed
MANAGED_SECRETS=(
    "DJANGO_SECRET_KEY"
    "POSTGRES_PASSWORD"
    "BACKUP_ENCRYPTION_KEY"
    "SSL_PRIVATE_KEY_PASSWORD"
    "REGISTRY_PASSWORD"
    "VAULT_TOKEN"
)

# File-based secrets management
create_secrets_file() {
    echo -e "${CYAN}Initializing file-based secrets storage...${NC}"
    
    # Validate secrets directory path
    local secrets_dir="$(dirname "$SECRETS_FILE_PATH")"
    if [[ "$secrets_dir" =~ \.\. ]] || [ ! -d "$(dirname "$secrets_dir")" ]; then
        echo -e "${RED}ERROR: Invalid secrets directory path${NC}"
        return 1
    fi
    
    # Create secrets directory with secure permissions
    umask 077  # Ensure restrictive permissions
    mkdir -p "$secrets_dir"
    chmod 700 "$secrets_dir"
    
    # Generate secrets file if it doesn't exist
    if [ ! -f "$SECRETS_FILE_PATH" ]; then
        echo -e "${BLUE}Creating encrypted secrets file...${NC}"
        
        # Create master key for encryption
        local master_key_file="${SECRETS_FILE_PATH}.key"
        if [ ! -f "$master_key_file" ]; then
            # Generate cryptographically secure key
            if ! openssl rand -base64 32 > "$master_key_file"; then
                echo -e "${RED}ERROR: Failed to generate master key${NC}"
                return 1
            fi
            chmod 600 "$master_key_file"
            chown root:root "$master_key_file"
        fi
        
        # Create empty secrets file with validation
        local temp_file="/tmp/secrets_init.$$"
        if echo '{}' | openssl enc -aes-256-cbc -salt -pbkdf2 \
            -pass "file:$master_key_file" \
            -out "$temp_file" 2>/dev/null; then
            
            # Verify we can decrypt what we just created
            if openssl enc -aes-256-cbc -d -pbkdf2 \
                -pass "file:$master_key_file" \
                -in "$temp_file" >/dev/null 2>&1; then
                
                mv "$temp_file" "$SECRETS_FILE_PATH"
                chmod 600 "$SECRETS_FILE_PATH"
                chown root:root "$SECRETS_FILE_PATH"
                echo -e "${GREEN}✓ Secrets file created: $SECRETS_FILE_PATH${NC}"
            else
                echo -e "${RED}ERROR: Failed to validate encrypted secrets file${NC}"
                rm -f "$temp_file"
                return 1
            fi
        else
            echo -e "${RED}ERROR: Failed to create encrypted secrets file${NC}"
            rm -f "$temp_file"
            return 1
        fi
    else
        echo -e "${GREEN}✓ Secrets file already exists${NC}"
    fi
}

# Read secret from file
read_secret_file() {
    local key="$1"
    local master_key_file="${SECRETS_FILE_PATH}.key"
    
    # Validate input
    if [ -z "$key" ]; then
        echo -e "${RED}ERROR: Secret key name cannot be empty${NC}"
        return 1
    fi
    
    # Validate key name (prevent injection)
    if [[ ! "$key" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
        echo -e "${RED}ERROR: Invalid secret key name format${NC}"
        return 1
    fi
    
    if [ ! -f "$SECRETS_FILE_PATH" ] || [ ! -f "$master_key_file" ]; then
        echo -e "${RED}ERROR: Secrets file not initialized${NC}"
        return 1
    fi
    
    # Decrypt and parse JSON with error handling
    local secrets_json
    if ! secrets_json=$(openssl enc -aes-256-cbc -d -pbkdf2 \
        -pass "file:$master_key_file" \
        -in "$SECRETS_FILE_PATH" 2>/dev/null); then
        echo -e "${RED}ERROR: Failed to decrypt secrets file${NC}"
        return 1
    fi
    
    # Validate JSON format
    if ! echo "$secrets_json" | python3 -m json.tool >/dev/null 2>&1; then
        echo -e "${RED}ERROR: Secrets file contains invalid JSON${NC}"
        return 1
    fi
    
    # Extract specific key using jq (if available) or basic parsing
    if command -v jq &> /dev/null; then
        echo "$secrets_json" | jq -r ".$key // empty"
    else
        # Basic parsing with validation
        echo "$secrets_json" | grep "\"$key\":" | sed 's/.*: *"\([^"]*\)".*/\1/' || true
    fi
}

# Write secret to file
write_secret_file() {
    local key="$1"
    local value="$2"
    local master_key_file="${SECRETS_FILE_PATH}.key"
    
    if [ ! -f "$SECRETS_FILE_PATH" ] || [ ! -f "$master_key_file" ]; then
        create_secrets_file
    fi
    
    # Decrypt current secrets
    local secrets_json=$(openssl enc -aes-256-cbc -d -pbkdf2 \
        -pass "file:$master_key_file" \
        -in "$SECRETS_FILE_PATH" 2>/dev/null)
    
    # Update JSON
    if command -v jq &> /dev/null; then
        secrets_json=$(echo "$secrets_json" | jq ".$key = \"$value\"")
    else
        # Basic JSON update (limited functionality)
        if echo "$secrets_json" | grep -q "\"$key\":"; then
            secrets_json=$(echo "$secrets_json" | sed "s/\"$key\": *\"[^\"]*\"/\"$key\": \"$value\"/")
        else
            secrets_json=$(echo "$secrets_json" | sed "s/}/{, \"$key\": \"$value\"}/")
        fi
    fi
    
    # Encrypt and save
    echo "$secrets_json" | openssl enc -aes-256-cbc -salt -pbkdf2 \
        -pass "file:$master_key_file" \
        -out "$SECRETS_FILE_PATH"
    
    echo -e "${GREEN}✓ Secret '$key' stored securely${NC}"
}

# HashiCorp Vault operations
read_secret_vault() {
    local key="$1"
    
    if [ -z "$VAULT_ADDR" ] || [ -z "$VAULT_TOKEN" ]; then
        echo -e "${RED}Error: Vault configuration missing${NC}"
        return 1
    fi
    
    # Use vault CLI if available, otherwise curl
    if command -v vault &> /dev/null; then
        export VAULT_ADDR VAULT_TOKEN
        vault kv get -field="$key" "$VAULT_PATH" 2>/dev/null
    else
        curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
            "$VAULT_ADDR/v1/$VAULT_PATH" | \
            jq -r ".data.data.$key // empty" 2>/dev/null
    fi
}

write_secret_vault() {
    local key="$1"
    local value="$2"
    
    if [ -z "$VAULT_ADDR" ] || [ -z "$VAULT_TOKEN" ]; then
        echo -e "${RED}Error: Vault configuration missing${NC}"
        return 1
    fi
    
    if command -v vault &> /dev/null; then
        export VAULT_ADDR VAULT_TOKEN
        vault kv patch "$VAULT_PATH" "$key=$value"
    else
        # Get existing secrets and update
        local existing=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
            "$VAULT_ADDR/v1/$VAULT_PATH" | jq -r '.data.data // {}')
        local updated=$(echo "$existing" | jq ".$key = \"$value\"")
        
        curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
            -H "Content-Type: application/json" \
            -X POST -d "{\"data\":$updated}" \
            "$VAULT_ADDR/v1/$VAULT_PATH" > /dev/null
    fi
    
    echo -e "${GREEN}✓ Secret '$key' stored in Vault${NC}"
}

# AWS Secrets Manager operations
read_secret_aws() {
    local key="$1"
    local secret_name="armguard/$key"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI not installed${NC}"
        return 1
    fi
    
    aws secretsmanager get-secret-value \
        --secret-id "$secret_name" \
        --region "$AWS_SECRETS_REGION" \
        --query 'SecretString' \
        --output text 2>/dev/null
}

write_secret_aws() {
    local key="$1"
    local value="$2"
    local secret_name="armguard/$key"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI not installed${NC}"
        return 1
    fi
    
    # Try to update existing secret, create if doesn't exist
    if aws secretsmanager update-secret \
        --secret-id "$secret_name" \
        --secret-string "$value" \
        --region "$AWS_SECRETS_REGION" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Secret '$key' updated in AWS Secrets Manager${NC}"
    else
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --secret-string "$value" \
            --region "$AWS_SECRETS_REGION" > /dev/null
        echo -e "${GREEN}✓ Secret '$key' created in AWS Secrets Manager${NC}"
    fi
}

# Azure Key Vault operations
read_secret_azure() {
    local key="$1"
    
    if ! command -v az &> /dev/null; then
        echo -e "${RED}Error: Azure CLI not installed${NC}"
        return 1
    fi
    
    if [ -z "$AZURE_KEY_VAULT_URL" ]; then
        echo -e "${RED}Error: Azure Key Vault URL not configured${NC}"
        return 1
    fi
    
    az keyvault secret show \
        --vault-url "$AZURE_KEY_VAULT_URL" \
        --name "$key" \
        --query 'value' \
        --output tsv 2>/dev/null
}

write_secret_azure() {
    local key="$1"
    local value="$2"
    
    if ! command -v az &> /dev/null; then
        echo -e "${RED}Error: Azure CLI not installed${NC}"
        return 1
    fi
    
    az keyvault secret set \
        --vault-url "$AZURE_KEY_VAULT_URL" \
        --name "$key" \
        --value "$value" > /dev/null
    
    echo -e "${GREEN}✓ Secret '$key' stored in Azure Key Vault${NC}"
}

# Generic secret operations
read_secret() {
    local key="$1"
    
    case "$SECRETS_BACKEND" in
        "file")
            read_secret_file "$key"
            ;;
        "vault")
            read_secret_vault "$key"
            ;;
        "aws")
            read_secret_aws "$key"
            ;;
        "azure")
            read_secret_azure "$key"
            ;;
        *)
            echo -e "${RED}Error: Unknown secrets backend: $SECRETS_BACKEND${NC}"
            return 1
            ;;
    esac
}

write_secret() {
    local key="$1"
    local value="$2"
    
    case "$SECRETS_BACKEND" in
        "file")
            write_secret_file "$key" "$value"
            ;;
        "vault")
            write_secret_vault "$key" "$value"
            ;;
        "aws")
            write_secret_aws "$key" "$value"
            ;;
        "azure")
            write_secret_azure "$key" "$value"
            ;;
        *)
            echo -e "${RED}Error: Unknown secrets backend: $SECRETS_BACKEND${NC}"
            return 1
            ;;
    esac
}

# Initialize secrets management
init_secrets() {
    echo -e "${CYAN}Initializing secrets management...${NC}"
    
    case "$SECRETS_BACKEND" in
        "file")
            create_secrets_file
            ;;
        "vault")
            echo -e "${BLUE}Using HashiCorp Vault at: $VAULT_ADDR${NC}"
            if [ -z "$VAULT_TOKEN" ]; then
                echo -e "${YELLOW}Warning: VAULT_TOKEN not set${NC}"
            fi
            ;;
        "aws")
            echo -e "${BLUE}Using AWS Secrets Manager in region: $AWS_SECRETS_REGION${NC}"
            ;;
        "azure")
            echo -e "${BLUE}Using Azure Key Vault: $AZURE_KEY_VAULT_URL${NC}"
            ;;
        *)
            echo -e "${RED}Error: Unknown secrets backend: $SECRETS_BACKEND${NC}"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}✓ Secrets management initialized${NC}"
}

# Generate missing secrets
generate_secrets() {
    echo -e "${CYAN}Generating missing secrets...${NC}"
    
    for secret_key in "${MANAGED_SECRETS[@]}"; do
        local existing_value=$(read_secret "$secret_key" 2>/dev/null)
        
        if [ -z "$existing_value" ]; then
            echo -e "${BLUE}Generating secret: $secret_key${NC}"
            
            case "$secret_key" in
                "DJANGO_SECRET_KEY")
                    local new_value=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || openssl rand -base64 50)
                    ;;
                *"PASSWORD"|*"KEY"|*"TOKEN")
                    local new_value=$(openssl rand -base64 32)
                    ;;
                *)
                    local new_value=$(openssl rand -base64 24)
                    ;;
            esac
            
            write_secret "$secret_key" "$new_value"
        else
            echo -e "${GREEN}✓ Secret exists: $secret_key${NC}"
        fi
    done
}

# List all secrets
list_secrets() {
    echo -e "${CYAN}Managed secrets:${NC}"
    
    for secret_key in "${MANAGED_SECRETS[@]}"; do
        local value=$(read_secret "$secret_key" 2>/dev/null)
        if [ -n "$value" ]; then
            echo -e "${GREEN}✓ $secret_key${NC}"
        else
            echo -e "${YELLOW}- $secret_key (not set)${NC}"
        fi
    done
}

# Export secrets to environment file
export_secrets() {
    local output_file="${1:-${PROJECT_DIR}/.env.secrets}"
    
    echo -e "${CYAN}Exporting secrets to: $output_file${NC}"
    
    echo "# ArmGuard Secrets - Generated $(date)" > "$output_file"
    echo "# DO NOT COMMIT THIS FILE TO VERSION CONTROL" >> "$output_file"
    echo "" >> "$output_file"
    
    for secret_key in "${MANAGED_SECRETS[@]}"; do
        local value=$(read_secret "$secret_key" 2>/dev/null)
        if [ -n "$value" ]; then
            echo "export $secret_key=\"$value\"" >> "$output_file"
        fi
    done
    
    chmod 600 "$output_file"
    echo -e "${GREEN}✓ Secrets exported to $output_file${NC}"
}

# Show configuration
show_config() {
    echo -e "${CYAN}Secrets Management Configuration:${NC}"
    echo -e "${BLUE}Backend:${NC} $SECRETS_BACKEND"
    
    case "$SECRETS_BACKEND" in
        "file")
            echo -e "${BLUE}Secrets File:${NC} $SECRETS_FILE_PATH"
            ;;
        "vault")
            echo -e "${BLUE}Vault Address:${NC} $VAULT_ADDR"
            echo -e "${BLUE}Vault Path:${NC} $VAULT_PATH"
            ;;
        "aws")
            echo -e "${BLUE}AWS Region:${NC} $AWS_SECRETS_REGION"
            ;;
        "azure")
            echo -e "${BLUE}Key Vault URL:${NC} $AZURE_KEY_VAULT_URL"
            ;;
    esac
}

# Main execution
main() {
    case "${1:-}" in
        "init")
            init_secrets
            ;;
        "generate")
            generate_secrets
            ;;
        "list")
            list_secrets
            ;;
        "get")
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: Secret key required${NC}"
                exit 1
            fi
            read_secret "$2"
            ;;
        "set")
            if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
                echo -e "${RED}Error: Secret key and value required${NC}"
                exit 1
            fi
            write_secret "$2" "$3"
            ;;
        "export")
            export_secrets "$2"
            ;;
        "config")
            show_config
            ;;
        *)
            echo "Usage: $0 {init|generate|list|get|set|export|config} [options]"
            echo ""
            echo "Commands:"
            echo "  init                Initialize secrets management"
            echo "  generate            Generate missing secrets"
            echo "  list                List all managed secrets"
            echo "  get <key>          Get secret value"
            echo "  set <key> <value>  Set secret value"
            echo "  export [file]      Export secrets to environment file"
            echo "  config             Show current configuration"
            echo ""
            echo "Examples:"
            echo "  $0 init"
            echo "  $0 generate"
            echo "  $0 get DJANGO_SECRET_KEY"
            echo "  $0 set API_TOKEN 'your-secret-token'"
            echo "  $0 export /etc/armguard/.env.secrets"
            echo ""
            echo "Backends:"
            echo "  file   - Encrypted file storage (default)"
            echo "  vault  - HashiCorp Vault"
            echo "  aws    - AWS Secrets Manager"
            echo "  azure  - Azure Key Vault"
            exit 1
            ;;
    esac
}

main "$@"
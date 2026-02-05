#!/bin/bash
# Media Directories Setup Script for ArmGuard
# Run this script after deployment to set up media directories with proper permissions

set -e  # Exit on error

echo "=========================================="
echo "ArmGuard Media Directories Setup"
echo "=========================================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
OWNER="www-data"
GROUP="www-data"
MEDIA_DIR="$PROJECT_DIR/core/media"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --owner)
            OWNER="$2"
            shift 2
            ;;
        --group)
            GROUP="$2"
            shift 2
            ;;
        --media-dir)
            MEDIA_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --owner USER      Set directory owner (default: www-data)"
            echo "  --group GROUP     Set directory group (default: www-data)"
            echo "  --media-dir PATH  Set media directory path (default: ../core/media)"
            echo "  --help            Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Configuration:"
echo "  Project Directory: $PROJECT_DIR"
echo "  Media Directory: $MEDIA_DIR"
echo "  Owner: $OWNER"
echo "  Group: $GROUP"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Warning: Not running as root."
    echo "   Ownership changes will be skipped."
    echo "   To set ownership, run: sudo $0"
    echo ""
    SKIP_OWNERSHIP=true
else
    SKIP_OWNERSHIP=false
fi

# Create main media directory
echo "Creating media directories..."
mkdir -p "$MEDIA_DIR"
echo "✓ Created $MEDIA_DIR"

# Create subdirectories
SUBDIRS=(
    "qr_codes/personnel"
    "qr_codes/items"
    "personnel/pictures"
    "users/profile_pictures"
    "transaction_forms"
)

# Check if user and group exist before creating directories
if [ "$SKIP_OWNERSHIP" = false ]; then
    if ! id "$OWNER" &>/dev/null; then
        echo "❌ Error: User '$OWNER' does not exist"
        echo "   Available users: $(cut -d: -f1 /etc/passwd | tr '\n' ' ')"
        exit 1
    fi
    if ! getent group "$GROUP" &>/dev/null; then
        echo "❌ Error: Group '$GROUP' does not exist"
        exit 1
    fi
    echo "✓ User and group validated"
    echo ""
fi

# Create each subdirectory with proper ownership immediately
for subdir in "${SUBDIRS[@]}"; do
    mkdir -p "$MEDIA_DIR/$subdir"
    
    # Set ownership immediately after creation (before next directory is created)
    if [ "$SKIP_OWNERSHIP" = false ]; then
        chown "$OWNER:$GROUP" "$MEDIA_DIR/$subdir"
        # Also set ownership on parent directories
        PARENT_DIR=$(dirname "$MEDIA_DIR/$subdir")
        while [ "$PARENT_DIR" != "$MEDIA_DIR" ] && [ "$PARENT_DIR" != "/" ]; do
            chown "$OWNER:$GROUP" "$PARENT_DIR"
            PARENT_DIR=$(dirname "$PARENT_DIR")
        done
    fi
    
    # Set permissions immediately
    chmod 775 "$MEDIA_DIR/$subdir"
    
    echo "✓ Created $MEDIA_DIR/$subdir"
done

# Set permissions and ownership on root media directory
echo ""
echo "Setting permissions (775) on root media directory..."
chmod 775 "$MEDIA_DIR"

if [ "$SKIP_OWNERSHIP" = false ]; then
    chown "$OWNER:$GROUP" "$MEDIA_DIR"
    echo "✓ Ownership set to $OWNER:$GROUP"
fi

echo "✓ Permissions set to 775 (rwxrwxr-x)"

# Final recursive pass to ensure everything is correct
if [ "$SKIP_OWNERSHIP" = false ]; then
    echo ""
    echo "Applying final recursive ownership pass..."
    chown -R "$OWNER:$GROUP" "$MEDIA_DIR"
    echo "✓ Final ownership pass complete"
fi

# Final recursive permission pass
echo ""
echo "Applying final recursive permission pass..."
chmod -R 775 "$MEDIA_DIR"
echo "✓ Final permission pass complete"

# Verify setup
echo ""
echo "=========================================="
echo "Verifying setup..."
echo "=========================================="

if [ -d "$MEDIA_DIR/qr_codes/personnel" ] && \
   [ -d "$MEDIA_DIR/qr_codes/items" ] && \
   [ -d "$MEDIA_DIR/personnel/pictures" ]; then
    echo "✓ All required directories exist"
else
    echo "❌ Some directories are missing"
    exit 1
fi

# Check permissions
PERMS=$(stat -c %a "$MEDIA_DIR" 2>/dev/null || stat -f %A "$MEDIA_DIR" 2>/dev/null)
if [ "$PERMS" = "775" ] || [ "$PERMS" = "2775" ]; then
    echo "✓ Permissions are correct"
else
    echo "⚠️  Warning: Permissions are $PERMS (expected 775)"
fi

# Display ownership info
if [ "$SKIP_OWNERSHIP" = false ]; then
    CURRENT_OWNER=$(stat -c '%U:%G' "$MEDIA_DIR" 2>/dev/null || stat -f '%Su:%Sg' "$MEDIA_DIR" 2>/dev/null)
    echo "✓ Owner: $CURRENT_OWNER"
fi

echo ""
echo "=========================================="
echo "✅ Media directories setup complete!"
echo "=========================================="
echo ""

if [ "$SKIP_OWNERSHIP" = true ]; then
    echo "⚠️  Note: To set proper ownership, run:"
    echo "   sudo $0 --owner=$OWNER --group=$GROUP"
    echo ""
fi

echo "Next steps:"
echo "1. Restart your Django application:"
echo "   sudo systemctl restart armguard.service"
echo ""
echo "2. Test file uploads and QR code generation"
echo ""

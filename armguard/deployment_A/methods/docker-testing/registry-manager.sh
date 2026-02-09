#!/bin/bash
################################################################################
# ArmGuard Container Registry Management Script
# 
# Handles building, tagging, pushing, and pulling container images
################################################################################

set -e

# Source registry configuration
if [ -f ".env.registry" ]; then
    source .env.registry
fi

# Default values
REGISTRY="${REGISTRY:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY_NAMESPACE="${REGISTRY_NAMESPACE:-armguard}"
DOCKER_BUILD_PLATFORMS="${DOCKER_BUILD_PLATFORMS:-linux/amd64,linux/arm64}"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# Construct image name
construct_image_name() {
    local service_name="$1"
    local tag="${2:-$IMAGE_TAG}"
    
    if [ -n "$REGISTRY" ]; then
        echo "$REGISTRY/$REGISTRY_NAMESPACE/$service_name:$tag"
    else
        echo "$REGISTRY_NAMESPACE/$service_name:$tag"
    fi
}

# Registry authentication
registry_login() {
    echo -e "${CYAN}Authenticating with container registry...${NC}"
    
    if [ -n "$REGISTRY_USERNAME" ] && [ -n "$REGISTRY_PASSWORD" ]; then
        echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin
        echo -e "${GREEN}✓ Registry authentication successful${NC}"
    elif [ -n "$REGISTRY" ]; then
        echo -e "${YELLOW}Warning: Registry specified but no credentials provided${NC}"
        echo "  Attempting login without credentials (may use cached credentials)"
        docker login "$REGISTRY" || echo -e "${YELLOW}Login failed, continuing anyway...${NC}"
    else
        echo -e "${BLUE}Using Docker Hub (no authentication required)${NC}"
    fi
}

# Build images
build_images() {
    local build_args="$1"
    local push_after_build="${2:-$DOCKER_PUSH_ON_BUILD}"
    
    echo -e "${CYAN}Building ArmGuard container images...${NC}"
    
    # Enable buildx for multi-platform builds
    if [[ "$DOCKER_BUILD_PLATFORMS" == *","* ]]; then
        echo -e "${BLUE}Enabling multi-platform builds...${NC}"
        docker buildx create --use --name armguard-builder 2>/dev/null || true
    fi
    
    # Build main application image
    local app_image=$(construct_image_name "armguard")
    echo -e "${BLUE}Building application image: $app_image${NC}"
    
    if [[ "$DOCKER_BUILD_PLATFORMS" == *","* ]]; then
        # Multi-platform build
        docker buildx build \
            --platform "$DOCKER_BUILD_PLATFORMS" \
            --tag "$app_image" \
            ${push_after_build:+--push} \
            ${build_args:+$build_args} \
            --file testing_environment/Dockerfile \
            .
    else
        # Single platform build
        docker build \
            --tag "$app_image" \
            ${build_args:+$build_args} \
            --file testing_environment/Dockerfile \
            .
        
        if [ "$push_after_build" = "true" ]; then
            docker push "$app_image"
        fi
    fi
    
    echo -e "${GREEN}✓ Build completed: $app_image${NC}"
}

# Push images to registry
push_images() {
    echo -e "${CYAN}Pushing images to registry...${NC}"
    
    # Registry authentication
    registry_login
    
    # Push application image
    local app_image=$(construct_image_name "armguard")
    echo -e "${BLUE}Pushing: $app_image${NC}"
    docker push "$app_image"
    
    echo -e "${GREEN}✓ All images pushed successfully${NC}"
}

# Pull images from registry
pull_images() {
    echo -e "${CYAN}Pulling images from registry...${NC}"
    
    # Registry authentication
    registry_login
    
    # Pull application image
    local app_image=$(construct_image_name "armguard")
    echo -e "${BLUE}Pulling: $app_image${NC}"
    docker pull "$app_image"
    
    echo -e "${GREEN}✓ All images pulled successfully${NC}"
}

# Tag images
tag_images() {
    local new_tag="$1"
    
    if [ -z "$new_tag" ]; then
        echo -e "${RED}Error: New tag required${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}Tagging images with: $new_tag${NC}"
    
    local current_image=$(construct_image_name "armguard")
    local new_image=$(construct_image_name "armguard" "$new_tag")
    
    docker tag "$current_image" "$new_image"
    echo -e "${GREEN}✓ Tagged: $current_image -> $new_image${NC}"
}

# Security scan
scan_images() {
    echo -e "${CYAN}Scanning images for vulnerabilities...${NC}"
    
    local app_image=$(construct_image_name "armguard")
    
    # Use trivy if available
    if command -v trivy &> /dev/null; then
        echo -e "${BLUE}Running Trivy security scan...${NC}"
        trivy image "$app_image"
    # Use docker scan if available
    elif docker scan --help &> /dev/null; then
        echo -e "${BLUE}Running Docker scan...${NC}"
        docker scan "$app_image"
    else
        echo -e "${YELLOW}No security scanner available. Install trivy or docker scan for vulnerability scanning.${NC}"
    fi
}

# Cleanup local images
cleanup_images() {
    echo -e "${CYAN}Cleaning up local images...${NC}"
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions (keep last 3)
    local app_image_base=$(construct_image_name "armguard" "")
    app_image_base="${app_image_base%:}"
    
    docker images "$app_image_base" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | \
        tail -n +2 | sort -k2 -r | tail -n +4 | awk '{print $1}' | \
        xargs -r docker rmi 2>/dev/null || true
    
    echo -e "${GREEN}✓ Cleanup completed${NC}"
}

# List available images
list_images() {
    echo -e "${CYAN}Available ArmGuard images:${NC}"
    
    local app_image_base=$(construct_image_name "armguard" "")
    app_image_base="${app_image_base%:}"
    
    docker images "$app_image_base" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

# Show current configuration
show_config() {
    echo -e "${CYAN}Current Container Registry Configuration:${NC}"
    echo -e "${BLUE}Registry:${NC} ${REGISTRY:-Docker Hub}"
    echo -e "${BLUE}Namespace:${NC} $REGISTRY_NAMESPACE"
    echo -e "${BLUE}Image Tag:${NC} $IMAGE_TAG"
    echo -e "${BLUE}Build Platforms:${NC} $DOCKER_BUILD_PLATFORMS"
    echo -e "${BLUE}Push on Build:${NC} ${DOCKER_PUSH_ON_BUILD:-false}"
    echo ""
    echo -e "${BLUE}Application Image:${NC} $(construct_image_name "armguard")"
}

# Main execution
main() {
    case "${1:-}" in
        "build")
            build_images "${@:2}"
            ;;
        "push")
            push_images
            ;;
        "pull")
            pull_images
            ;;
        "tag")
            tag_images "$2"
            ;;
        "scan")
            scan_images
            ;;
        "cleanup")
            cleanup_images
            ;;
        "list")
            list_images
            ;;
        "config")
            show_config
            ;;
        "login")
            registry_login
            ;;
        *)
            echo "Usage: $0 {build|push|pull|tag|scan|cleanup|list|config|login} [options]"
            echo ""
            echo "Commands:"
            echo "  build [args]    Build container images"
            echo "  push            Push images to registry"
            echo "  pull            Pull images from registry"
            echo "  tag <new-tag>   Tag images with new tag"
            echo "  scan            Run security vulnerability scan"
            echo "  cleanup         Clean up old local images"
            echo "  list            List available images"
            echo "  config          Show current configuration"
            echo "  login           Authenticate with registry"
            echo ""
            echo "Examples:"
            echo "  $0 build"
            echo "  $0 build --build-arg ENV=production"
            echo "  $0 tag v2.1.0"
            echo "  $0 push"
            echo ""
            echo "Configuration:"
            echo "  Edit .env.registry to configure registry settings"
            exit 1
            ;;
    esac
}

main "$@"
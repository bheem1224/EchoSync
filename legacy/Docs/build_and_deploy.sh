#!/bin/bash

# SoulSync Build and Deployment Script
# Handles building Docker image and deploying to Docker Hub

set -e  # Exit on error

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-boulderbadgedad}"
IMAGE_NAME="soulsync"
IMAGE_TAG="${1:-latest}"
REGISTRY="${DOCKER_USERNAME}/${IMAGE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Verify Docker is installed
verify_docker() {
    print_header "Verifying Docker Installation"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    print_success "Docker and Docker Compose found"
    docker --version
    docker-compose --version
}

# Run tests
run_tests() {
    print_header "Running Tests"
    
    if command -v pytest &> /dev/null; then
        print_warning "Running test suite..."
        if pytest tests/core/ -q; then
            print_success "All tests passed"
        else
            print_error "Tests failed"
            exit 1
        fi
    else
        print_warning "pytest not installed, skipping tests"
        print_warning "To run tests: pip install pytest && pytest tests/core/ -q"
    fi
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"
    
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile not found in current directory"
        exit 1
    fi
    
    print_warning "Building image: ${REGISTRY}:${IMAGE_TAG}"
    
    if docker build -t "${REGISTRY}:${IMAGE_TAG}" .; then
        print_success "Docker image built successfully"
        docker images | grep "${REGISTRY}" | head -1
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    
    # Also tag as latest if not already latest
    if [ "${IMAGE_TAG}" != "latest" ]; then
        docker tag "${REGISTRY}:${IMAGE_TAG}" "${REGISTRY}:latest"
        print_success "Tagged as latest"
    fi
}

# Test Docker image locally
test_image_locally() {
    print_header "Testing Docker Image Locally"
    
    print_warning "Starting container for testing..."
    
    # Create temp directories for testing
    mkdir -p ./test-data/data ./test-data/logs ./test-data/downloads
    
    # Run container with test volumes
    CONTAINER_ID=$(docker run -d \
        --name soulsync-test \
        -p 8008:8008 \
        -v "$(pwd)/test-data/data:/data" \
        -v "$(pwd)/test-data/logs:/app/logs" \
        -v "$(pwd)/test-data/downloads:/app/downloads" \
        -e FLASK_ENV=production \
        "${REGISTRY}:${IMAGE_TAG}" 2>/dev/null || echo "")
    
    if [ -z "$CONTAINER_ID" ]; then
        print_error "Failed to start test container"
        return 1
    fi
    
    print_success "Container started: $CONTAINER_ID"
    
    # Wait for container to be healthy
    print_warning "Waiting for container to be ready (30 seconds)..."
    sleep 30
    
    # Check if container is still running
    if docker ps | grep -q soulsync-test; then
        print_success "Container is running"
        
        # Try to access the health endpoint
        if docker exec soulsync-test curl -f http://localhost:8008/ 2>/dev/null | grep -q "html"; then
            print_success "Web server is responding"
        else
            print_warning "Could not verify web server response"
        fi
    else
        print_error "Container stopped"
        docker logs soulsync-test
        return 1
    fi
    
    # Clean up test container
    print_warning "Cleaning up test container..."
    docker stop soulsync-test 2>/dev/null || true
    docker rm soulsync-test 2>/dev/null || true
    rm -rf ./test-data
    
    print_success "Image testing complete"
}

# Login to Docker Hub
docker_login() {
    print_header "Docker Hub Authentication"
    
    if docker ps > /dev/null 2>&1; then
        print_success "Already authenticated with Docker"
    else
        print_warning "Please log in to Docker Hub"
        docker login
    fi
}

# Push image to Docker Hub
push_image() {
    print_header "Pushing Image to Docker Hub"
    
    print_warning "Pushing ${REGISTRY}:${IMAGE_TAG}..."
    
    if docker push "${REGISTRY}:${IMAGE_TAG}"; then
        print_success "Image pushed successfully"
        echo ""
        echo "Image available at: https://hub.docker.com/r/${REGISTRY}/tags"
    else
        print_error "Failed to push image"
        exit 1
    fi
}

# Deployment instructions
show_deployment_instructions() {
    print_header "Deployment Instructions"
    
    cat << EOF

${GREEN}✓ Build and push completed successfully!${NC}

To deploy the application:

${YELLOW}Option 1: Using docker-compose (Recommended)${NC}
  1. Create data directories:
     mkdir -p ./data ./logs ./downloads

  2. Update docker-compose.yml if needed

  3. Start the application:
     docker-compose up -d

  4. Access at: http://localhost:8008

${YELLOW}Option 2: Direct docker run${NC}
  docker run -d \
    --name soulsync-webui \
    -p 8008:8008 \
    -v \$(pwd)/data:/data \
    -v \$(pwd)/logs:/app/logs \
    -v \$(pwd)/downloads:/app/downloads \
    -e FLASK_ENV=production \
    ${REGISTRY}:${IMAGE_TAG}

${YELLOW}Useful Commands${NC}
  View logs:
    docker-compose logs -f soulsync

  Check health:
    docker-compose ps

  Stop:
    docker-compose down

${YELLOW}Secrets Management${NC}
  Your credentials are now stored encrypted in the database!
  
  Security best practices:
  - Never commit config/.encryption_key to git
  - Backup database/config.db and config/.encryption_key
  - Use HTTPS in production (with reverse proxy)

For more details, see BUILD_AND_DEPLOY.md

EOF
}

# Main menu
main_menu() {
    print_header "SoulSync Build & Deployment"
    
    echo "Select action:"
    echo "1) Build Docker image (local testing)"
    echo "2) Build and test Docker image"
    echo "3) Build, test, and push to Docker Hub"
    echo "4) Just test existing image"
    echo "5) Show deployment instructions"
    echo "6) Exit"
    echo ""
    
    read -p "Enter choice [1-6]: " choice
    
    case $choice in
        1)
            verify_docker
            build_image
            show_deployment_instructions
            ;;
        2)
            verify_docker
            run_tests
            build_image
            test_image_locally
            show_deployment_instructions
            ;;
        3)
            verify_docker
            run_tests
            build_image
            test_image_locally
            docker_login
            push_image
            show_deployment_instructions
            ;;
        4)
            verify_docker
            test_image_locally
            ;;
        5)
            show_deployment_instructions
            ;;
        6)
            print_success "Exiting"
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            main_menu
            ;;
    esac
}

# Run main menu if script is run directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    # Check if we're in the SoulSync directory
    if [ ! -f "Dockerfile" ] || [ ! -f "web_server.py" ]; then
        print_error "This script must be run from the SoulSync root directory"
        exit 1
    fi
    
    # If arguments provided, run non-interactive mode
    if [ $# -gt 0 ]; then
        case $1 in
            build)
                verify_docker
                build_image
                ;;
            test)
                verify_docker
                test_image_locally
                ;;
            push)
                verify_docker
                build_image
                docker_login
                push_image
                ;;
            *)
                echo "Usage: $0 {build|test|push}"
                exit 1
                ;;
        esac
    else
        main_menu
    fi
fi

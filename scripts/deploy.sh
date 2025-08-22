#!/bin/bash

# Kamikaze AI Backend Deployment Script
# This script handles zero-downtime deployment with rollback capabilities

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_IMAGE_NAME="${DOCKER_IMAGE_NAME:-kamikaze-ai-backend}"
CONTAINER_NAME="${CONTAINER_NAME:-kamikaze-ai-backend}"
BACKUP_CONTAINER_NAME="${BACKUP_CONTAINER_NAME:-kamikaze-ai-backend-backup}"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8000/health}"
ENVIRONMENT="${ENVIRONMENT:-production}"
DEPLOYMENT_TIMEOUT="${DEPLOYMENT_TIMEOUT:-300}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    log_success "Docker is running"
}

# Function to check health with comprehensive validation
check_health() {
    local max_attempts=${1:-30}
    local attempt=1
    
    log_info "Starting health check validation (max attempts: $max_attempts)..."
    
    while [ $attempt -le $max_attempts ]; do
        # Basic health check
        if curl -f -s "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
            log_success "Basic health check passed"
            
            # API functionality check
            if curl -f -s "http://localhost:8000/api/info" | grep -q "Kamikaze"; then
                log_success "API functionality verified"
                return 0
            else
                log_warning "API functionality check failed, retrying..."
            fi
        fi
        
        log_info "Health check attempt $attempt/$max_attempts..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Function to backup current container
backup_current_container() {
    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_info "Creating backup of current container..."
        docker stop "$CONTAINER_NAME" --time=30 || true
        docker rename "$CONTAINER_NAME" "$BACKUP_CONTAINER_NAME" || true
        log_success "Current container backed up as $BACKUP_CONTAINER_NAME"
    else
        log_info "No existing container to backup"
    fi
}

# Function to start new container
start_new_container() {
    local image_tag="$1"
    
    log_info "Starting new container with image: $image_tag"
    
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p 8000:8000 \
        -e ENVIRONMENT="$ENVIRONMENT" \
        -e USE_AWS_SECRETS=true \
        -e AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}" \
        -e LOG_LEVEL="${LOG_LEVEL:-INFO}" \
        -e ENABLE_FILE_LOGGING=true \
        -e MAX_LOG_FILES=10 \
        -e PYTHONPATH=/app/src \
        --log-driver=json-file \
        --log-opt max-size=100m \
        --log-opt max-file=5 \
        "$image_tag"
    
    log_success "New container started"
}

# Function to rollback to backup container
rollback_to_backup() {
    log_warning "Initiating rollback procedure..."
    
    # Stop failed container
    docker stop "$CONTAINER_NAME" || true
    docker rm "$CONTAINER_NAME" || true
    
    # Restore backup if available
    if docker ps -a | grep -q "$BACKUP_CONTAINER_NAME"; then
        log_info "Restoring backup container..."
        docker rename "$BACKUP_CONTAINER_NAME" "$CONTAINER_NAME"
        docker start "$CONTAINER_NAME"
        
        # Verify rollback
        sleep 10
        if check_health 10; then
            log_success "Rollback successful - service restored"
            return 0
        else
            log_error "Rollback failed - manual intervention required"
            return 1
        fi
    else
        log_error "No backup available - manual intervention required"
        return 1
    fi
}

# Function to cleanup old resources
cleanup_old_resources() {
    log_info "Cleaning up old resources..."
    
    # Remove backup container
    if docker ps -a | grep -q "$BACKUP_CONTAINER_NAME"; then
        log_info "Removing backup container..."
        docker rm "$BACKUP_CONTAINER_NAME" || true
    fi
    
    # Clean up old images (keep last 3)
    log_info "Cleaning up old Docker images..."
    docker images "$DOCKER_IMAGE_NAME" --format "{{.Tag}}" | \
        grep -v latest | sort -r | tail -n +4 | \
        xargs -r -I {} docker rmi "$DOCKER_IMAGE_NAME:{}" 2>/dev/null || true
    
    # Clean up unused Docker resources
    docker system prune -f
    
    log_success "Cleanup completed"
}

# Function to validate deployment
validate_deployment() {
    log_info "Running deployment validation..."
    
    # Check container status
    local container_status
    container_status=$(docker ps --filter name="$CONTAINER_NAME" --format "{{.Status}}")
    
    if [[ $container_status == *"Up"* ]]; then
        log_success "Container is running: $container_status"
    else
        log_error "Container is not running properly"
        return 1
    fi
    
    # Performance check
    log_info "Running performance check..."
    local response_time
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "$HEALTH_CHECK_URL")
    log_info "Health endpoint response time: ${response_time}s"
    
    # Log deployment info
    log_info "Deployment Summary:"
    log_info "  Environment: $ENVIRONMENT"
    log_info "  Container: $CONTAINER_NAME"
    log_info "  Health URL: $HEALTH_CHECK_URL"
    log_info "  Response Time: ${response_time}s"
    
    return 0
}

# Main deployment function
deploy() {
    local image_tag="$1"
    
    log_info "Starting Kamikaze AI deployment to $ENVIRONMENT..."
    log_info "Image: $image_tag"
    
    # Pre-deployment checks
    check_docker
    
    # Backup current container
    backup_current_container
    
    # Start new container
    start_new_container "$image_tag"
    
    # Wait for container to initialize
    log_info "Waiting for container to initialize..."
    sleep 20
    
    # Perform health check
    if check_health; then
        log_success "Deployment completed successfully!"
        
        # Validate deployment
        if validate_deployment; then
            # Cleanup old resources
            cleanup_old_resources
            log_success "🎉 Deployment validation passed!"
            return 0
        else
            log_warning "Deployment validation failed, but service is running"
            return 0
        fi
    else
        log_error "Deployment failed - health check unsuccessful"
        
        # Show failed container logs
        log_info "Failed deployment logs:"
        docker logs "$CONTAINER_NAME" --tail 50 || true
        
        # Attempt rollback
        if rollback_to_backup; then
            log_warning "Rollback completed, but deployment failed"
            exit 1
        else
            log_error "Both deployment and rollback failed - manual intervention required"
            exit 2
        fi
    fi
}

# Script usage
usage() {
    echo "Usage: $0 <docker_image_tag>"
    echo "Example: $0 kamikaze-ai-backend:latest"
    echo ""
    echo "Environment variables:"
    echo "  ENVIRONMENT - Deployment environment (default: production)"
    echo "  CONTAINER_NAME - Container name (default: kamikaze-ai-backend)"
    echo "  HEALTH_CHECK_URL - Health check URL (default: http://localhost:8000/health)"
    echo "  DEPLOYMENT_TIMEOUT - Deployment timeout in seconds (default: 300)"
}

# Main script execution
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi
    
    local image_tag="$1"
    
    log_info "Kamikaze AI Deployment Script"
    log_info "=============================="
    
    deploy "$image_tag"
}

# Execute main function with all arguments
main "$@"

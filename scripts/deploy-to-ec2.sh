#!/bin/bash
# Kamikaze-be Backend - EC2 Deployment Script
# Deploys the application to the specified EC2 instance

set -e

# Configuration
EC2_INSTANCE_ID="i-07e35a954b57372a3"
EC2_PUBLIC_IP="34.238.167.174"
EC2_USER="ubuntu"
APP_NAME="kamikaze-be"
DOCKER_IMAGE="kamikaze-be:latest"
CONTAINER_NAME="kamikaze-app"
APP_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Kamikaze-be Backend Deployment to EC2${NC}"
echo -e "${BLUE}Instance: ${EC2_INSTANCE_ID} (${EC2_PUBLIC_IP})${NC}"

# Function to run commands on EC2
run_on_ec2() {
    if [ -f ~/.ssh/id_rsa ]; then
        # Use SSH key from GitHub secrets
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_rsa ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
    else
        # Fallback to default SSH
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
    fi
}

# Function to copy files to EC2
copy_to_ec2() {
    if [ -f ~/.ssh/id_rsa ]; then
        # Use SSH key from GitHub secrets
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_rsa "$1" ${EC2_USER}@${EC2_PUBLIC_IP}:"$2"
    else
        # Fallback to default SCP
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$1" ${EC2_USER}@${EC2_PUBLIC_IP}:"$2"
    fi
}

# Check if EC2 instance is accessible
echo -e "${YELLOW}📡 Checking EC2 instance connectivity...${NC}"
if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${EC2_USER}@${EC2_PUBLIC_IP} "echo 'Connection successful'"; then
    echo -e "${RED}❌ Cannot connect to EC2 instance${NC}"
    exit 1
fi
echo -e "${GREEN}✅ EC2 instance is accessible${NC}"

# Install Docker if not present
echo -e "${YELLOW}🐳 Ensuring Docker is installed on EC2...${NC}"
run_on_ec2 "
    if ! command -v docker &> /dev/null; then
        echo 'Installing Docker...'
        sudo yum update -y
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker ${EC2_USER}
        echo 'Docker installed successfully'
    else
        echo 'Docker is already installed'
        sudo systemctl start docker
    fi
"

# Stop and remove existing container
echo -e "${YELLOW}🛑 Stopping existing application...${NC}"
run_on_ec2 "
    if docker ps -q -f name=${CONTAINER_NAME}; then
        echo 'Stopping existing container...'
        docker stop ${CONTAINER_NAME} || true
        docker rm ${CONTAINER_NAME} || true
    fi
"

# Build Docker image on EC2
echo -e "${YELLOW}🔨 Building Docker image on EC2...${NC}"

# Create deployment directory
run_on_ec2 "mkdir -p /home/${EC2_USER}/${APP_NAME}"

# Copy application files
echo -e "${YELLOW}📦 Copying application files...${NC}"
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    --exclude='*.pyc' --exclude='.env' \
    ./ ${EC2_USER}@${EC2_PUBLIC_IP}:/home/${EC2_USER}/${APP_NAME}/

# Build the Docker image
run_on_ec2 "
    cd /home/${EC2_USER}/${APP_NAME}
    echo 'Building Docker image...'
    docker build -t ${DOCKER_IMAGE} .
"

# Run the new container
echo -e "${YELLOW}🚀 Starting new application container...${NC}"
run_on_ec2 "
    docker run -d \
        --name ${CONTAINER_NAME} \
        --restart unless-stopped \
        -p ${APP_PORT}:${APP_PORT} \
        -e ENVIRONMENT=production \
        -e USE_AWS_SECRETS=true \
        -e AWS_DEFAULT_REGION=us-east-1 \
        -e DB_HOST=\"${DB_HOST:-}\" \
        -e DB_PORT=\"${DB_PORT:-5432}\" \
        -e DB_NAME=\"${DB_NAME:-kamikaze}\" \
        -e DB_USER=\"${DB_USER:-}\" \
        -e DB_PASSWORD=\"${DB_PASSWORD:-}\" \
        ${DOCKER_IMAGE}
"

# Wait for application to start
echo -e "${YELLOW}⏳ Waiting for application to start...${NC}"
sleep 30

# Health check
echo -e "${YELLOW}🏥 Performing health check...${NC}"
if run_on_ec2 "curl -f http://localhost:${APP_PORT}/health"; then
    echo -e "${GREEN}✅ Application is healthy and running${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo -e "${YELLOW}📋 Container logs:${NC}"
    run_on_ec2 "docker logs ${CONTAINER_NAME}"
    exit 1
fi

# Show deployment status
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo -e "  Instance: ${EC2_INSTANCE_ID}"
echo -e "  Public IP: ${EC2_PUBLIC_IP}"
echo -e "  Application URL: http://${EC2_PUBLIC_IP}:${APP_PORT}"
echo -e "  Health Check: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"

# Show container status
echo -e "${BLUE}🐳 Container Status:${NC}"
run_on_ec2 "docker ps -f name=${CONTAINER_NAME}"

echo -e "${GREEN}✅ FluxTrader Backend deployment completed!${NC}"

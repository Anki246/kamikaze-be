#!/bin/bash
# Manual Deployment Script for FluxTrader Backend
# Use this to deploy directly to EC2 when CI/CD is not available

set -e

# Configuration
EC2_PUBLIC_IP="34.238.167.174"
EC2_USER="ec2-user"
APP_NAME="fluxtrader-backend"
DOCKER_IMAGE="fluxtrader:latest"
CONTAINER_NAME="fluxtrader-app"
APP_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Manual FluxTrader Backend Deployment${NC}"
echo -e "${BLUE}Target: ${EC2_PUBLIC_IP}${NC}"

# Function to run commands on EC2
run_on_ec2() {
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
}

# Check if we can connect to EC2
echo -e "${YELLOW}📡 Testing EC2 connectivity...${NC}"
if ! run_on_ec2 "echo 'Connected successfully'"; then
    echo -e "${RED}❌ Cannot connect to EC2. Please check:${NC}"
    echo -e "  - SSH key is configured"
    echo -e "  - EC2 instance is running"
    echo -e "  - Security groups allow SSH access"
    exit 1
fi

# Install Docker if needed
echo -e "${YELLOW}🐳 Ensuring Docker is installed...${NC}"
run_on_ec2 "
    if ! command -v docker &> /dev/null; then
        echo 'Installing Docker...'
        sudo yum update -y
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker ${EC2_USER}
    fi
    sudo systemctl start docker
"

# Stop existing container
echo -e "${YELLOW}🛑 Stopping existing container...${NC}"
run_on_ec2 "
    if docker ps -q -f name=${CONTAINER_NAME}; then
        docker stop ${CONTAINER_NAME}
        docker rm ${CONTAINER_NAME}
    fi
"

# Create deployment directory and copy files
echo -e "${YELLOW}📦 Copying application files...${NC}"
run_on_ec2 "mkdir -p /home/${EC2_USER}/${APP_NAME}"

# Copy files using rsync
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    --exclude='*.pyc' --exclude='.env' \
    ./ ${EC2_USER}@${EC2_PUBLIC_IP}:/home/${EC2_USER}/${APP_NAME}/

# Build Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
run_on_ec2 "
    cd /home/${EC2_USER}/${APP_NAME}
    docker build -t ${DOCKER_IMAGE} .
"

# Run the container with environment variables
echo -e "${YELLOW}🚀 Starting FluxTrader container...${NC}"
run_on_ec2 "
    docker run -d \
        --name ${CONTAINER_NAME} \
        --restart unless-stopped \
        -p ${APP_PORT}:${APP_PORT} \
        -e ENVIRONMENT=production \
        -e USE_AWS_SECRETS=false \
        -e AWS_DEFAULT_REGION=us-east-1 \
        -e DB_HOST=localhost \
        -e DB_PORT=5432 \
        -e DB_NAME=kamikaze \
        -e DB_USER=postgres \
        -e DB_PASSWORD=admin2025 \
        -e PYTHONPATH=/app/src \
        -e PYTHONUNBUFFERED=1 \
        ${DOCKER_IMAGE}
"

# Wait for startup
echo -e "${YELLOW}⏳ Waiting for application to start...${NC}"
sleep 15

# Check if container is running
echo -e "${YELLOW}🔍 Checking container status...${NC}"
if run_on_ec2 "docker ps -f name=${CONTAINER_NAME} --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"; then
    echo -e "${GREEN}✅ Container is running${NC}"
else
    echo -e "${RED}❌ Container failed to start${NC}"
    echo -e "${YELLOW}📋 Container logs:${NC}"
    run_on_ec2 "docker logs ${CONTAINER_NAME}"
    exit 1
fi

# Test application health
echo -e "${YELLOW}🏥 Testing application health...${NC}"
sleep 10

if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✅ Application is healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed, but container is running${NC}"
    echo -e "${YELLOW}📋 Container logs:${NC}"
    run_on_ec2 "docker logs --tail 20 ${CONTAINER_NAME}"
fi

# Show deployment summary
echo -e "\n${GREEN}🎉 Deployment Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "📍 Instance: ${EC2_PUBLIC_IP}"
echo -e "🌐 Application: http://${EC2_PUBLIC_IP}:${APP_PORT}"
echo -e "🏥 Health Check: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
echo -e "📚 API Docs: http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
echo -e "🐳 Container: ${CONTAINER_NAME}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Show container status
echo -e "\n${BLUE}🐳 Container Status:${NC}"
run_on_ec2 "docker ps -f name=${CONTAINER_NAME}"

echo -e "\n${GREEN}✅ Manual deployment completed!${NC}"
echo -e "${YELLOW}💡 To view logs: ssh ${EC2_USER}@${EC2_PUBLIC_IP} 'docker logs -f ${CONTAINER_NAME}'${NC}"

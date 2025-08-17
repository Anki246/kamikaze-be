#!/bin/bash
# Direct Kamikaze-be Deployment Script using PEM key

set -e

# Configuration
EC2_INSTANCE_ID="i-07e35a954b57372a3"
EC2_PUBLIC_IP="34.238.167.174"
EC2_USER="ubuntu"
APP_NAME="kamikaze-be"
DOCKER_IMAGE="kamikaze-be:latest"
CONTAINER_NAME="kamikaze-app"
APP_PORT="8000"
SSH_KEY="$HOME/.ssh/kamikaze-ec2-key.pem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Kamikaze-be to EC2${NC}"
echo -e "${BLUE}Instance: ${EC2_INSTANCE_ID} (${EC2_PUBLIC_IP})${NC}"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ SSH key not found: $SSH_KEY${NC}"
    echo -e "${YELLOW}💡 Copying from Downloads...${NC}"
    cp ~/Downloads/kmkz-key-ec2.pem "$SSH_KEY"
    chmod 600 "$SSH_KEY"
fi

# Function to run commands on EC2
run_on_ec2() {
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i "$SSH_KEY" ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
}

# Test SSH connection with different approaches
echo -e "${YELLOW}📡 Testing SSH connection...${NC}"
if run_on_ec2 "echo 'Connected successfully'"; then
    echo -e "${GREEN}✅ SSH connection successful with ubuntu${NC}"
elif EC2_USER="ec2-user" && run_on_ec2 "echo 'Connected successfully'"; then
    echo -e "${GREEN}✅ SSH connection successful with ec2-user${NC}"
else
    echo -e "${YELLOW}⚠️  Direct SSH failed, trying with sudo access...${NC}"
    # Try connecting without key and use sudo for commands
    EC2_USER="ubuntu"
    if ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${EC2_USER}@${EC2_PUBLIC_IP} "echo 'Connected successfully'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH connection successful without key${NC}"
        # Update function to not use key
        run_on_ec2() {
            ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
        }
    else
        echo -e "${RED}❌ All SSH connection methods failed${NC}"
        echo -e "${YELLOW}💡 Please ensure the EC2 instance allows SSH access${NC}"
        exit 1
    fi
fi

# Install Docker if needed
echo -e "${YELLOW}🐳 Installing Docker...${NC}"
run_on_ec2 "
    if ! command -v docker &> /dev/null; then
        echo 'Installing Docker...'
        if command -v yum &> /dev/null; then
            sudo yum update -y
            sudo yum install -y docker git curl
        elif command -v apt &> /dev/null; then
            sudo apt update -y
            sudo apt install -y docker.io git curl
        fi
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker \$USER
        echo 'Docker installed successfully'
    else
        echo 'Docker already installed, starting service...'
        sudo systemctl start docker
        sudo systemctl status docker --no-pager
    fi
"

# Clone repository
echo -e "${YELLOW}📥 Cloning repository...${NC}"
run_on_ec2 "
    cd /home/\$USER
    rm -rf ${APP_NAME}
    git clone https://github.com/Anki246/kamikaze-be.git ${APP_NAME}
    cd ${APP_NAME}
"

# Stop existing container
echo -e "${YELLOW}🛑 Stopping existing container...${NC}"
run_on_ec2 "
    echo 'Stopping existing containers...'
    sudo docker stop ${CONTAINER_NAME} 2>/dev/null || echo 'No container to stop'
    sudo docker rm ${CONTAINER_NAME} 2>/dev/null || echo 'No container to remove'
    sudo docker ps -a | grep ${CONTAINER_NAME} || echo 'Container cleaned up'
"

# Build Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
run_on_ec2 "
    cd /home/\$USER/${APP_NAME}
    echo 'Building Docker image...'
    sudo docker build -t ${DOCKER_IMAGE} . --no-cache
    echo 'Docker image built successfully'
"

# Run container
echo -e "${YELLOW}🚀 Starting Kamikaze-be container...${NC}"
run_on_ec2 "
    sudo docker run -d \
        --name ${CONTAINER_NAME} \
        --restart unless-stopped \
        -p ${APP_PORT}:${APP_PORT} \
        -e ENVIRONMENT=production \
        -e USE_AWS_SECRETS=false \
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
sleep 20

# Check container status
echo -e "${YELLOW}🔍 Checking container status...${NC}"
run_on_ec2 "
    sudo docker ps -f name=${CONTAINER_NAME}
    echo ''
    echo 'Container logs:'
    sudo docker logs --tail 10 ${CONTAINER_NAME}
"

# Test application
echo -e "${YELLOW}🏥 Testing application...${NC}"
if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✅ Kamikaze-be is running and healthy!${NC}"
    
    # Show response
    echo -e "${BLUE}Health response:${NC}"
    curl -s "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" | head -3
else
    echo -e "${YELLOW}⚠️  External health check failed, testing locally...${NC}"
    run_on_ec2 "curl -s http://localhost:${APP_PORT}/health || echo 'Local health check also failed'"
fi

# Show deployment summary
echo -e "\n${GREEN}🎉 Kamikaze-be Deployment Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "📍 Instance: ${EC2_INSTANCE_ID}"
echo -e "🌐 Public IP: ${EC2_PUBLIC_IP}"
echo -e "🚀 Application: http://${EC2_PUBLIC_IP}:${APP_PORT}"
echo -e "🏥 Health Check: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
echo -e "📚 API Docs: http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
echo -e "🐳 Container: ${CONTAINER_NAME}"
echo -e "👤 User: ${EC2_USER}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${GREEN}✅ Kamikaze-be deployment completed!${NC}"

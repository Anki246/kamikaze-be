#!/bin/bash
# Kamikaze-be Backend - EC2 Deployment Script
# Deploys the application to the specified EC2 instance

set -e

# Configuration
EC2_INSTANCE_ID="i-08bc5befe61de1a51"
EC2_PUBLIC_IP="3.81.64.108"
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
    # Try multiple SSH key locations
    if [ -f ~/.ssh/id_rsa ]; then
        # Use SSH key from GitHub secrets (id_rsa)
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_rsa ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
    elif [ -f ~/.ssh/kmkz-new-ec2key.pem ]; then
        # Use local kmkz-new-ec2key.pem
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/kmkz-new-ec2key.pem ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
    else
        # Fallback to default SSH
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
    fi
}

# Function to copy files to EC2
copy_to_ec2() {
    # Try multiple SSH key locations
    if [ -f ~/.ssh/id_rsa ]; then
        # Use SSH key from GitHub secrets (id_rsa)
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_rsa "$1" ${EC2_USER}@${EC2_PUBLIC_IP}:"$2"
    elif [ -f ~/.ssh/kmkz-new-ec2key.pem ]; then
        # Use local kmkz-new-ec2key.pem
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/kmkz-new-ec2key.pem "$1" ${EC2_USER}@${EC2_PUBLIC_IP}:"$2"
    else
        # Fallback to default SCP
        scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$1" ${EC2_USER}@${EC2_PUBLIC_IP}:"$2"
    fi
}

# Debug SSH key setup
echo -e "${YELLOW}🔍 Debugging SSH key setup...${NC}"
if [ -f ~/.ssh/id_rsa ]; then
    echo -e "${GREEN}✅ SSH key file exists at ~/.ssh/id_rsa${NC}"
    echo -e "${BLUE}📋 SSH key permissions: $(ls -la ~/.ssh/id_rsa)${NC}"
    echo -e "${BLUE}📋 SSH key fingerprint: $(ssh-keygen -lf ~/.ssh/id_rsa)${NC}"
else
    echo -e "${RED}❌ SSH key file not found at ~/.ssh/id_rsa${NC}"
fi

# Check if EC2 instance is accessible
echo -e "${YELLOW}📡 Checking EC2 instance connectivity...${NC}"

# Try different SSH keys and users
SSH_SUCCESS=false

# Try with id_rsa (GitHub Actions)
if [ -f ~/.ssh/id_rsa ]; then
    echo -e "${BLUE}🔑 Trying SSH with id_rsa key...${NC}"
    for user in ubuntu ec2-user; do
        echo -e "${BLUE}  Testing user: ${user}${NC}"
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/id_rsa ${user}@${EC2_PUBLIC_IP} "echo 'Connection successful'" 2>/dev/null; then
            echo -e "${GREEN}✅ Connected successfully with user: ${user}${NC}"
            EC2_USER=${user}
            SSH_SUCCESS=true
            break
        fi
    done
fi

# Try with kmkz-new-ec2key.pem (local)
if [ "$SSH_SUCCESS" = false ] && [ -f ~/.ssh/kmkz-new-ec2key.pem ]; then
    echo -e "${BLUE}🔑 Trying SSH with kmkz-new-ec2key.pem key...${NC}"
    for user in ubuntu ec2-user; do
        echo -e "${BLUE}  Testing user: ${user}${NC}"
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/kmkz-new-ec2key.pem ${user}@${EC2_PUBLIC_IP} "echo 'Connection successful'" 2>/dev/null; then
            echo -e "${GREEN}✅ Connected successfully with user: ${user}${NC}"
            EC2_USER=${user}
            SSH_SUCCESS=true
            break
        fi
    done
fi

# Try without key (fallback)
if [ "$SSH_SUCCESS" = false ]; then
    echo -e "${BLUE}🔑 Trying SSH without key...${NC}"
    for user in ubuntu ec2-user; do
        echo -e "${BLUE}  Testing user: ${user}${NC}"
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${user}@${EC2_PUBLIC_IP} "echo 'Connection successful'" 2>/dev/null; then
            echo -e "${GREEN}✅ Connected successfully with user: ${user}${NC}"
            EC2_USER=${user}
            SSH_SUCCESS=true
            break
        fi
    done
fi

if [ "$SSH_SUCCESS" = false ]; then
    echo -e "${RED}❌ Cannot connect to EC2 instance with any method${NC}"
    echo -e "${YELLOW}🔍 Running verbose SSH for debugging...${NC}"
    if [ -f ~/.ssh/id_rsa ]; then
        ssh -v -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/id_rsa ubuntu@${EC2_PUBLIC_IP} "echo 'Connection successful'" || true
    elif [ -f ~/.ssh/kmkz-new-ec2key.pem ]; then
        ssh -v -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/kmkz-new-ec2key.pem ubuntu@${EC2_PUBLIC_IP} "echo 'Connection successful'" || true
    fi
    exit 1
fi
echo -e "${GREEN}✅ EC2 instance is accessible${NC}"

# Install Docker if not present
echo -e "${YELLOW}🐳 Ensuring Docker is installed on EC2...${NC}"
run_on_ec2 "
    if ! command -v docker &> /dev/null; then
        echo 'Installing Docker...'
        # Detect OS and use appropriate package manager
        if command -v apt &> /dev/null; then
            # Ubuntu/Debian
            sudo apt update -y
            sudo apt install -y docker.io
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -a -G docker ${EC2_USER}
        elif command -v yum &> /dev/null; then
            # Amazon Linux/CentOS/RHEL
            sudo yum update -y
            sudo yum install -y docker
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -a -G docker ${EC2_USER}
        else
            echo 'Unsupported OS for automatic Docker installation'
            exit 1
        fi
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
if [ -f ~/.ssh/id_rsa ]; then
    # Use SSH key from GitHub secrets
    rsync -avz -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_rsa" \
        --exclude='.git' --exclude='venv' --exclude='__pycache__' \
        --exclude='*.pyc' --exclude='.env' \
        ./ ${EC2_USER}@${EC2_PUBLIC_IP}:/home/${EC2_USER}/${APP_NAME}/
elif [ -f ~/.ssh/kmkz-new-ec2key.pem ]; then
    # Use local kmkz-new-ec2key.pem
    rsync -avz -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/kmkz-new-ec2key.pem" \
        --exclude='.git' --exclude='venv' --exclude='__pycache__' \
        --exclude='*.pyc' --exclude='.env' \
        ./ ${EC2_USER}@${EC2_PUBLIC_IP}:/home/${EC2_USER}/${APP_NAME}/
else
    # Fallback to default rsync
    rsync -avz -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
        --exclude='.git' --exclude='venv' --exclude='__pycache__' \
        --exclude='*.pyc' --exclude='.env' \
        ./ ${EC2_USER}@${EC2_PUBLIC_IP}:/home/${EC2_USER}/${APP_NAME}/
fi

# Build the Docker image
run_on_ec2 "
    cd /home/${EC2_USER}/${APP_NAME}
    echo 'Building Docker image...'
    docker build -t ${DOCKER_IMAGE} .
"

# Debug environment variables
echo -e "${YELLOW}🔍 Debugging environment variables...${NC}"
echo -e "${BLUE}DB_HOST: ${DB_HOST:-'NOT SET'}${NC}"
echo -e "${BLUE}DB_PORT: ${DB_PORT:-'NOT SET'}${NC}"
echo -e "${BLUE}DB_NAME: ${DB_NAME:-'NOT SET'}${NC}"
echo -e "${BLUE}DB_USER: ${DB_USER:-'NOT SET'}${NC}"
echo -e "${BLUE}DB_PASSWORD: ${DB_PASSWORD:+'SET'}${DB_PASSWORD:-'NOT SET'}${NC}"
echo -e "${BLUE}GITHUB_ACTIONS: ${GITHUB_ACTIONS:-'NOT SET'}${NC}"

# Run the new container
echo -e "${YELLOW}🚀 Starting new application container...${NC}"

# Determine if running in GitHub Actions or locally
if [ "${GITHUB_ACTIONS}" = "true" ]; then
    echo -e "${GREEN}🔧 Running in GitHub Actions - using RDS database${NC}"
    # Use RDS environment variables from GitHub secrets
    DB_HOST_VALUE="${DB_HOST}"
    DB_PORT_VALUE="${DB_PORT}"
    DB_NAME_VALUE="${DB_NAME}"
    DB_USER_VALUE="${DB_USER}"
    DB_PASSWORD_VALUE="${DB_PASSWORD}"
    USE_AWS_SECRETS_VALUE="false"

    # Validate RDS credentials
    if [ -z "${DB_HOST_VALUE}" ] || [ -z "${DB_USER_VALUE}" ] || [ -z "${DB_PASSWORD_VALUE}" ]; then
        echo -e "${RED}❌ Missing RDS credentials in GitHub secrets${NC}"
        echo -e "${YELLOW}💡 Please ensure DB_HOST, DB_USER, DB_PASSWORD are set in Production environment${NC}"
        exit 1
    fi

    echo -e "${BLUE}🗄️  Using RDS database: ${DB_HOST_VALUE}${NC}"
else
    echo -e "${YELLOW}🔧 Running locally - using localhost database${NC}"
    # Set default values for local testing (localhost)
    DB_HOST_VALUE="${DB_HOST:-localhost}"
    DB_PORT_VALUE="${DB_PORT:-5432}"
    DB_NAME_VALUE="${DB_NAME:-kamikaze}"
    DB_USER_VALUE="${DB_USER:-postgres}"
    DB_PASSWORD_VALUE="${DB_PASSWORD:-admin2025}"
    USE_AWS_SECRETS_VALUE="false"

    echo -e "${BLUE}🗄️  Using localhost database for testing${NC}"
fi

echo -e "${BLUE}Using values:${NC}"
echo -e "${BLUE}  DB_HOST: ${DB_HOST_VALUE}${NC}"
echo -e "${BLUE}  DB_PORT: ${DB_PORT_VALUE}${NC}"
echo -e "${BLUE}  DB_NAME: ${DB_NAME_VALUE}${NC}"
echo -e "${BLUE}  DB_USER: ${DB_USER_VALUE}${NC}"
echo -e "${BLUE}  USE_AWS_SECRETS: ${USE_AWS_SECRETS_VALUE}${NC}"

run_on_ec2 "
    docker run -d \
        --name ${CONTAINER_NAME} \
        --restart unless-stopped \
        -p ${APP_PORT}:${APP_PORT} \
        -e ENVIRONMENT=production \
        -e USE_AWS_SECRETS=${USE_AWS_SECRETS_VALUE} \
        -e AWS_DEFAULT_REGION=us-east-1 \
        -e DB_HOST=\"${DB_HOST_VALUE}\" \
        -e DB_PORT=\"${DB_PORT_VALUE}\" \
        -e DB_NAME=\"${DB_NAME_VALUE}\" \
        -e DB_USER=\"${DB_USER_VALUE}\" \
        -e DB_PASSWORD=\"${DB_PASSWORD_VALUE}\" \
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
echo -e "  Instance: ${EC2_INSTANCE_ID} (kmkz-ec2)"
echo -e "  Public IP: ${EC2_PUBLIC_IP}"
echo -e "  Private IP: 172.31.36.119"
echo -e "  Database: kmkz-database-new"
echo -e "  Application URL: http://${EC2_PUBLIC_IP}:${APP_PORT}"
echo -e "  Health Check: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"

# Show container status
echo -e "${BLUE}🐳 Container Status:${NC}"
run_on_ec2 "docker ps -f name=${CONTAINER_NAME}"

echo -e "${GREEN}✅ Kamikaze-be Backend deployment completed!${NC}"

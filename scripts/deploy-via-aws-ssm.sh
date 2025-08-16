#!/bin/bash
# AWS Systems Manager Deployment Script
# Alternative deployment method when SSH keys are not available

set -e

# Configuration
EC2_INSTANCE_ID="i-07e35a954b57372a3"
EC2_PUBLIC_IP="34.238.167.174"
APP_NAME="fluxtrader-backend"
DOCKER_IMAGE="fluxtrader:latest"
CONTAINER_NAME="fluxtrader-app"
APP_PORT="8000"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AWS Systems Manager Deployment to EC2${NC}"
echo -e "${BLUE}Instance: ${EC2_INSTANCE_ID} (${EC2_PUBLIC_IP})${NC}"

# Function to run commands via AWS SSM
run_ssm_command() {
    local command="$1"
    local description="$2"
    
    echo -e "${YELLOW}📡 Running: ${description}${NC}"
    
    # Send command via SSM
    command_id=$(aws ssm send-command \
        --instance-ids "${EC2_INSTANCE_ID}" \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[\"${command}\"]" \
        --region "${AWS_REGION}" \
        --query 'Command.CommandId' \
        --output text)
    
    if [ -z "$command_id" ]; then
        echo -e "${RED}❌ Failed to send command via SSM${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Command ID: ${command_id}${NC}"
    
    # Wait for command to complete
    echo -e "${YELLOW}⏳ Waiting for command to complete...${NC}"
    aws ssm wait command-executed \
        --command-id "${command_id}" \
        --instance-id "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}"
    
    # Get command output
    output=$(aws ssm get-command-invocation \
        --command-id "${command_id}" \
        --instance-id "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}" \
        --query 'StandardOutputContent' \
        --output text)
    
    error_output=$(aws ssm get-command-invocation \
        --command-id "${command_id}" \
        --instance-id "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}" \
        --query 'StandardErrorContent' \
        --output text)
    
    # Check command status
    status=$(aws ssm get-command-invocation \
        --command-id "${command_id}" \
        --instance-id "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}" \
        --query 'Status' \
        --output text)
    
    if [ "$status" = "Success" ]; then
        echo -e "${GREEN}✅ ${description} completed successfully${NC}"
        if [ -n "$output" ] && [ "$output" != "None" ]; then
            echo -e "${BLUE}Output:${NC}"
            echo "$output"
        fi
        return 0
    else
        echo -e "${RED}❌ ${description} failed${NC}"
        if [ -n "$error_output" ] && [ "$error_output" != "None" ]; then
            echo -e "${RED}Error:${NC}"
            echo "$error_output"
        fi
        return 1
    fi
}

# Check if SSM agent is available
echo -e "${YELLOW}🔍 Checking SSM connectivity...${NC}"
if ! aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text | grep -q "Online"; then
    echo -e "${RED}❌ EC2 instance is not available via SSM${NC}"
    echo -e "${YELLOW}💡 Falling back to direct HTTP deployment...${NC}"
    ./scripts/deploy-via-http.sh
    exit $?
fi

echo -e "${GREEN}✅ SSM connectivity confirmed${NC}"

# Install Docker and Git
run_ssm_command "
sudo yum update -y
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
" "Installing Docker and Git"

# Clone repository and build
run_ssm_command "
cd /home/ec2-user
rm -rf ${APP_NAME}
git clone https://github.com/Anki246/kamikaze-be.git ${APP_NAME}
cd ${APP_NAME}
sudo docker build -t ${DOCKER_IMAGE} .
" "Cloning repository and building Docker image"

# Stop existing container
run_ssm_command "
sudo docker stop ${CONTAINER_NAME} 2>/dev/null || true
sudo docker rm ${CONTAINER_NAME} 2>/dev/null || true
" "Stopping existing container"

# Start new container
run_ssm_command "
sudo docker run -d \
    --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -p ${APP_PORT}:${APP_PORT} \
    -e ENVIRONMENT=production \
    -e USE_AWS_SECRETS=false \
    -e AWS_DEFAULT_REGION=${AWS_REGION} \
    -e DB_HOST=\"${DB_HOST:-localhost}\" \
    -e DB_PORT=\"${DB_PORT:-5432}\" \
    -e DB_NAME=\"${DB_NAME:-kamikaze}\" \
    -e DB_USER=\"${DB_USER:-postgres}\" \
    -e DB_PASSWORD=\"${DB_PASSWORD:-admin2025}\" \
    -e PYTHONPATH=/app/src \
    -e PYTHONUNBUFFERED=1 \
    ${DOCKER_IMAGE}
" "Starting new container"

# Wait for startup
echo -e "${YELLOW}⏳ Waiting for application to start...${NC}"
sleep 30

# Check container status
run_ssm_command "
sudo docker ps -f name=${CONTAINER_NAME}
sudo docker logs --tail 10 ${CONTAINER_NAME}
" "Checking container status"

# Test application health
echo -e "${YELLOW}🏥 Testing application health...${NC}"
if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✅ Application is healthy and accessible!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed, checking logs...${NC}"
    run_ssm_command "sudo docker logs --tail 20 ${CONTAINER_NAME}" "Getting container logs"
fi

# Show deployment summary
echo -e "\n${GREEN}🎉 SSM Deployment Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "📍 Instance: ${EC2_INSTANCE_ID}"
echo -e "🌐 Public IP: ${EC2_PUBLIC_IP}"
echo -e "🚀 Application: http://${EC2_PUBLIC_IP}:${APP_PORT}"
echo -e "🏥 Health Check: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
echo -e "📚 API Docs: http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
echo -e "🐳 Container: ${CONTAINER_NAME}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${GREEN}✅ AWS SSM deployment completed!${NC}"

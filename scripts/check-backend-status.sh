#!/bin/bash
# Quick Backend Status Check Script

set -e

# Configuration
EC2_PUBLIC_IP="34.238.167.174"
EC2_USER="ec2-user"
APP_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 FluxTrader Backend Status Check${NC}"
echo -e "${BLUE}Target: ${EC2_PUBLIC_IP}:${APP_PORT}${NC}"

# Function to run commands on EC2
run_on_ec2() {
    ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
}

# Check EC2 connectivity
echo -e "\n${YELLOW}📡 EC2 Connectivity:${NC}"
if run_on_ec2 "echo 'Connected'" 2>/dev/null; then
    echo -e "${GREEN}✅ EC2 is accessible${NC}"
else
    echo -e "${RED}❌ Cannot connect to EC2${NC}"
    exit 1
fi

# Check if port is open
echo -e "\n${YELLOW}🔌 Port Status:${NC}"
if nc -z -w5 ${EC2_PUBLIC_IP} ${APP_PORT} 2>/dev/null; then
    echo -e "${GREEN}✅ Port ${APP_PORT} is open${NC}"
else
    echo -e "${RED}❌ Port ${APP_PORT} is not accessible${NC}"
fi

# Check processes
echo -e "\n${YELLOW}🔍 Backend Processes:${NC}"
run_on_ec2 "ps aux | grep -E '(python.*app.py|uvicorn.*main:app)' | grep -v grep || echo 'No backend processes found'"

# Check Docker containers
echo -e "\n${YELLOW}🐳 Docker Containers:${NC}"
run_on_ec2 "docker ps -a | grep fluxtrader || echo 'No FluxTrader containers found'"

# Check port usage
echo -e "\n${YELLOW}🔌 Port Usage:${NC}"
run_on_ec2 "sudo netstat -tlnp | grep :${APP_PORT} || echo 'Port ${APP_PORT} not in use'"

# Test health endpoint
echo -e "\n${YELLOW}🏥 Health Check:${NC}"
if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✅ Health endpoint is responding${NC}"
    echo -e "${BLUE}Response:${NC}"
    curl -s "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" | python3 -m json.tool 2>/dev/null || curl -s "http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
else
    echo -e "${RED}❌ Health endpoint is not responding${NC}"
fi

# Test API docs
echo -e "\n${YELLOW}📚 API Documentation:${NC}"
if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/docs" > /dev/null; then
    echo -e "${GREEN}✅ API docs are accessible${NC}"
else
    echo -e "${RED}❌ API docs are not accessible${NC}"
fi

# Show recent logs if available
echo -e "\n${YELLOW}📋 Recent Logs:${NC}"
run_on_ec2 "
    if [ -f /home/${EC2_USER}/fluxtrader-backend/backend.log ]; then
        echo 'Last 10 lines from backend.log:'
        tail -10 /home/${EC2_USER}/fluxtrader-backend/backend.log
    else
        echo 'No backend.log found'
    fi
"

# Show Docker logs if container exists
run_on_ec2 "
    if docker ps -q -f name=fluxtrader-app; then
        echo 'Last 10 lines from Docker container:'
        docker logs --tail 10 fluxtrader-app
    fi
" 2>/dev/null || true

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🌐 URLs to test:${NC}"
echo -e "  Health: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
echo -e "  API Docs: http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
echo -e "  Root: http://${EC2_PUBLIC_IP}:${APP_PORT}/"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

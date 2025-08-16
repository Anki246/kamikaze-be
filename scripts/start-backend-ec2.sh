#!/bin/bash
# Direct Backend Startup Script for EC2
# Runs the FluxTrader backend directly on EC2 without Docker

set -e

# Configuration
EC2_PUBLIC_IP="34.238.167.174"
EC2_USER="ec2-user"
APP_NAME="fluxtrader-backend"
APP_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting FluxTrader Backend Directly on EC2${NC}"
echo -e "${BLUE}Target: ${EC2_PUBLIC_IP}:${APP_PORT}${NC}"

# Function to run commands on EC2
run_on_ec2() {
    ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_PUBLIC_IP} "$1"
}

# Check connectivity
echo -e "${YELLOW}📡 Testing EC2 connectivity...${NC}"
if ! run_on_ec2 "echo 'Connected successfully'"; then
    echo -e "${RED}❌ Cannot connect to EC2${NC}"
    exit 1
fi

# Copy application files
echo -e "${YELLOW}📦 Copying application files...${NC}"
run_on_ec2 "mkdir -p /home/${EC2_USER}/${APP_NAME}"

rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    --exclude='*.pyc' \
    ./ ${EC2_USER}@${EC2_PUBLIC_IP}:/home/${EC2_USER}/${APP_NAME}/

# Install Python and dependencies
echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
run_on_ec2 "
    cd /home/${EC2_USER}/${APP_NAME}
    
    # Install Python 3.11 if not available
    if ! command -v python3.11 &> /dev/null; then
        sudo yum update -y
        sudo yum install -y python3 python3-pip
    fi
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo 'Python environment ready'
"

# Kill any existing backend process
echo -e "${YELLOW}🛑 Stopping existing backend processes...${NC}"
run_on_ec2 "
    # Kill any existing Python processes running on port 8000
    sudo pkill -f 'python.*app.py' || true
    sudo pkill -f 'uvicorn.*main:app' || true
    
    # Kill any process using port 8000
    sudo fuser -k 8000/tcp || true
    
    sleep 2
"

# Start the backend
echo -e "${YELLOW}🚀 Starting FluxTrader backend...${NC}"
run_on_ec2 "
    cd /home/${EC2_USER}/${APP_NAME}
    source venv/bin/activate
    
    # Set environment variables
    export PYTHONPATH=/home/${EC2_USER}/${APP_NAME}/src
    export PYTHONUNBUFFERED=1
    export ENVIRONMENT=production
    export USE_AWS_SECRETS=false
    export DB_HOST=localhost
    export DB_PORT=5432
    export DB_NAME=kamikaze
    export DB_USER=postgres
    export DB_PASSWORD=admin2025
    
    # Start the backend in background
    nohup python app.py --host 0.0.0.0 --port ${APP_PORT} > backend.log 2>&1 &
    
    echo 'Backend started in background'
    echo 'Process ID:' \$!
"

# Wait for startup
echo -e "${YELLOW}⏳ Waiting for backend to start...${NC}"
sleep 10

# Check if backend is running
echo -e "${YELLOW}🔍 Checking backend status...${NC}"
if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✅ Backend is running and healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed, checking logs...${NC}"
    run_on_ec2 "cd /home/${EC2_USER}/${APP_NAME} && tail -20 backend.log"
fi

# Show process status
echo -e "${YELLOW}📊 Process status:${NC}"
run_on_ec2 "ps aux | grep -E '(python.*app.py|uvicorn.*main:app)' | grep -v grep || echo 'No backend processes found'"

# Show port status
echo -e "${YELLOW}🔌 Port status:${NC}"
run_on_ec2 "sudo netstat -tlnp | grep :${APP_PORT} || echo 'Port ${APP_PORT} not in use'"

# Show deployment summary
echo -e "\n${GREEN}🎉 Backend Startup Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "📍 Instance: ${EC2_PUBLIC_IP}"
echo -e "🌐 Application: http://${EC2_PUBLIC_IP}:${APP_PORT}"
echo -e "🏥 Health Check: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
echo -e "📚 API Docs: http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
echo -e "📋 Logs: ssh ${EC2_USER}@${EC2_PUBLIC_IP} 'cd ${APP_NAME} && tail -f backend.log'"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${GREEN}✅ Backend startup completed!${NC}"
echo -e "${YELLOW}💡 To stop: ssh ${EC2_USER}@${EC2_PUBLIC_IP} 'sudo pkill -f python.*app.py'${NC}"

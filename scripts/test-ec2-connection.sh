#!/bin/bash
# Test EC2 Connection Script
# Tests different connection methods to determine what works

set -e

# Configuration
EC2_PUBLIC_IP="34.238.167.174"
APP_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Testing EC2 Connection Methods${NC}"
echo -e "${BLUE}Target: ${EC2_PUBLIC_IP}${NC}"

# Test basic connectivity
echo -e "\n${YELLOW}📡 Testing basic connectivity...${NC}"
if ping -c 3 ${EC2_PUBLIC_IP} > /dev/null 2>&1; then
    echo -e "${GREEN}✅ EC2 instance is reachable via ping${NC}"
else
    echo -e "${RED}❌ EC2 instance is not reachable via ping${NC}"
fi

# Test port 22 (SSH)
echo -e "\n${YELLOW}🔌 Testing SSH port (22)...${NC}"
if nc -z -w5 ${EC2_PUBLIC_IP} 22 2>/dev/null; then
    echo -e "${GREEN}✅ SSH port 22 is open${NC}"
else
    echo -e "${RED}❌ SSH port 22 is not accessible${NC}"
fi

# Test application port
echo -e "\n${YELLOW}🔌 Testing application port (${APP_PORT})...${NC}"
if nc -z -w5 ${EC2_PUBLIC_IP} ${APP_PORT} 2>/dev/null; then
    echo -e "${GREEN}✅ Application port ${APP_PORT} is open${NC}"
else
    echo -e "${RED}❌ Application port ${APP_PORT} is not accessible${NC}"
fi

# Test common web ports
echo -e "\n${YELLOW}🌐 Testing common web ports...${NC}"
for port in 80 443 8080; do
    if nc -z -w5 ${EC2_PUBLIC_IP} $port 2>/dev/null; then
        echo -e "${GREEN}✅ Port $port is open${NC}"
    else
        echo -e "${RED}❌ Port $port is not accessible${NC}"
    fi
done

# Test SSH connection with different users
echo -e "\n${YELLOW}🔑 Testing SSH connections...${NC}"

users=("ec2-user" "ubuntu" "admin" "root")
for user in "${users[@]}"; do
    echo -e "${BLUE}Testing SSH with user: $user${NC}"
    
    # Test with key-based auth (no password)
    if timeout 10 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=no -o ConnectTimeout=5 ${user}@${EC2_PUBLIC_IP} "echo 'Connected as $user'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH works with user $user (key-based)${NC}"
        WORKING_USER=$user
        break
    else
        echo -e "${RED}❌ SSH failed with user $user (key-based)${NC}"
    fi
    
    # Test with password auth enabled
    if timeout 10 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PasswordAuthentication=yes -o ConnectTimeout=5 ${user}@${EC2_PUBLIC_IP} "echo 'Connected as $user'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH works with user $user (password-based)${NC}"
        WORKING_USER=$user
        break
    else
        echo -e "${RED}❌ SSH failed with user $user (password-based)${NC}"
    fi
done

# Test HTTP endpoints
echo -e "\n${YELLOW}🌐 Testing HTTP endpoints...${NC}"
endpoints=("/" "/health" "/docs" "/api/info")
for endpoint in "${endpoints[@]}"; do
    url="http://${EC2_PUBLIC_IP}:${APP_PORT}${endpoint}"
    if curl -f -s --max-time 10 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $url is responding${NC}"
    else
        echo -e "${RED}❌ $url is not responding${NC}"
    fi
done

# Summary
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Connection Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ ! -z "${WORKING_USER:-}" ]; then
    echo -e "${GREEN}✅ SSH Access: Working with user '$WORKING_USER'${NC}"
    echo -e "${YELLOW}💡 You can use: ssh $WORKING_USER@$EC2_PUBLIC_IP${NC}"
else
    echo -e "${RED}❌ SSH Access: No working SSH connection found${NC}"
    echo -e "${YELLOW}💡 Possible solutions:${NC}"
    echo -e "   1. Add your SSH public key to the instance"
    echo -e "   2. Enable password authentication"
    echo -e "   3. Use AWS Session Manager"
    echo -e "   4. Check security groups allow SSH (port 22)"
fi

echo -e "\n${YELLOW}🔧 Next Steps:${NC}"
echo -e "1. If SSH works, run: ./scripts/manual-deploy.sh"
echo -e "2. If no SSH, use AWS Console to access the instance"
echo -e "3. Manual commands to run on the instance:"
echo -e "   - Install Docker: sudo yum install -y docker && sudo systemctl start docker"
echo -e "   - Clone repo: git clone https://github.com/Anki246/kamikaze-be.git"
echo -e "   - Build: cd kamikaze-be && docker build -t fluxtrader ."
echo -e "   - Run: docker run -d -p 8000:8000 --name fluxtrader-app fluxtrader"

echo -e "\n${BLUE}🌐 URLs to test after deployment:${NC}"
echo -e "   http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
echo -e "   http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
echo -e "   http://${EC2_PUBLIC_IP}:${APP_PORT}/"

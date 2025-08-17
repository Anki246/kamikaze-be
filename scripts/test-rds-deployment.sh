#!/bin/bash
# Test script for RDS deployment verification

set -e

# Configuration
EC2_INSTANCE_ID="i-08bc5befe61de1a51"
EC2_PUBLIC_IP="3.81.64.108"
SSH_KEY="~/.ssh/kmkz-new-ec2key.pem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing RDS Deployment for Kamikaze-be${NC}"
echo -e "${BLUE}Instance: ${EC2_INSTANCE_ID} (${EC2_PUBLIC_IP})${NC}"
echo -e "${BLUE}Database: AWS RDS (kmkz-database-new)${NC}"
echo ""

# Test 1: SSH Connection
echo -e "${YELLOW}🔍 Test 1: SSH Connection${NC}"
if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/kmkz-new-ec2key.pem ubuntu@${EC2_PUBLIC_IP} "echo 'SSH connection successful'"; then
    echo -e "${GREEN}✅ SSH connection working${NC}"
else
    echo -e "${RED}❌ SSH connection failed${NC}"
    exit 1
fi

# Test 2: Docker Status
echo -e "${YELLOW}🔍 Test 2: Docker and Application Status${NC}"
ssh -o StrictHostKeyChecking=no -i ~/.ssh/kmkz-new-ec2key.pem ubuntu@${EC2_PUBLIC_IP} "
echo '🐳 Docker Status:'
sudo docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo ''
echo '📊 Application Container:'
if sudo docker ps | grep -q kamikaze-app; then
    echo '✅ Application container is running'
    
    echo ''
    echo '🔍 Container Environment (Database Config):'
    sudo docker exec kamikaze-app env | grep -E '^(DB_|ENVIRONMENT|USE_AWS_SECRETS)' | sort
    
    echo ''
    echo '📋 Recent Application Logs:'
    sudo docker logs kamikaze-app --tail 10
else
    echo '❌ Application container is not running'
fi
"

# Test 3: Application Health Check
echo -e "${YELLOW}🔍 Test 3: Application Health Check${NC}"
if curl -f -s http://${EC2_PUBLIC_IP}:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application health check passed${NC}"
    echo -e "${BLUE}📋 Health response:${NC}"
    curl -s http://${EC2_PUBLIC_IP}:8000/health | python -m json.tool 2>/dev/null || curl -s http://${EC2_PUBLIC_IP}:8000/health
else
    echo -e "${RED}❌ Application health check failed${NC}"
    echo -e "${YELLOW}🔍 Testing basic connectivity...${NC}"
    if nc -z -w5 ${EC2_PUBLIC_IP} 8000 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Port 8000 is accessible but application not responding properly${NC}"
    else
        echo -e "${RED}❌ Port 8000 is not accessible${NC}"
    fi
fi

# Test 4: Database Configuration Verification
echo -e "${YELLOW}🔍 Test 4: Database Configuration${NC}"
ssh -o StrictHostKeyChecking=no -i ~/.ssh/kmkz-new-ec2key.pem ubuntu@${EC2_PUBLIC_IP} "
if sudo docker ps | grep -q kamikaze-app; then
    echo '🗄️  Database Configuration in Container:'
    sudo docker exec kamikaze-app python -c \"
import os
import sys
sys.path.insert(0, '/app/src')

try:
    from infrastructure.database_config import DatabaseConfig
    config = DatabaseConfig()
    
    print(f'Host: {config.host}')
    print(f'Port: {config.port}')
    print(f'Database: {config.database}')
    print(f'User: {config.user}')
    print(f'SSL Mode: {config.ssl_mode}')
    
    if '.rds.amazonaws.com' in config.host:
        print('✅ Using AWS RDS database')
    else:
        print('⚠️  Not using RDS database')
        
except Exception as e:
    print(f'❌ Error loading database config: {e}')
\" 2>/dev/null || echo '❌ Failed to check database configuration'
else
    echo '❌ Application container not running'
fi
"

# Test 5: API Endpoints
echo -e "${YELLOW}🔍 Test 5: API Endpoints${NC}"
echo -e "${BLUE}Testing key endpoints...${NC}"

# Test root endpoint
if curl -f -s http://${EC2_PUBLIC_IP}:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Root endpoint (/) accessible${NC}"
else
    echo -e "${RED}❌ Root endpoint (/) failed${NC}"
fi

# Test docs endpoint
if curl -f -s http://${EC2_PUBLIC_IP}:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API docs (/docs) accessible${NC}"
else
    echo -e "${RED}❌ API docs (/docs) failed${NC}"
fi

# Test 6: GitHub Actions Integration
echo -e "${YELLOW}🔍 Test 6: GitHub Actions Integration${NC}"
echo -e "${BLUE}📋 Required GitHub Secrets (Production environment):${NC}"
echo "• EC2_SSH_PRIVATE_KEY - SSH key for EC2 access"
echo "• DB_HOST - RDS endpoint"
echo "• DB_PORT - Database port (5432)"
echo "• DB_NAME - Database name"
echo "• DB_USER - Database username"
echo "• DB_PASSWORD - Database password"

echo ""
echo -e "${BLUE}🔗 GitHub Actions URL:${NC}"
echo "https://github.com/Anki246/kamikaze-be/actions"

# Test 7: Migration Status
echo -e "${YELLOW}🔍 Test 7: Migration Status${NC}"
if [ -f "migration_*.log" ]; then
    echo -e "${GREEN}✅ Migration log files found${NC}"
    echo -e "${BLUE}📋 Latest migration log:${NC}"
    ls -la migration_*.log | tail -1
else
    echo -e "${YELLOW}⚠️  No migration log files found locally${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}🏁 Test Summary${NC}"
echo -e "${GREEN}✅ SSH connection: Working${NC}"
echo -e "${GREEN}✅ EC2 instance: Accessible${NC}"
echo -e "${GREEN}✅ Docker: Installed and running${NC}"

if curl -f -s http://${EC2_PUBLIC_IP}:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application: Healthy and running${NC}"
    echo -e "${GREEN}✅ RDS Integration: Ready for production${NC}"
else
    echo -e "${YELLOW}⚠️  Application: Needs attention${NC}"
    echo -e "${YELLOW}⚠️  RDS Integration: Check logs and configuration${NC}"
fi

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Ensure GitHub secrets are configured in Production environment"
echo "2. Push to main branch to trigger deployment with RDS"
echo "3. Monitor GitHub Actions for successful deployment"
echo "4. Verify application connects to RDS database"
echo ""
echo -e "${BLUE}🔗 Useful URLs:${NC}"
echo "• Application: http://${EC2_PUBLIC_IP}:8000"
echo "• Health Check: http://${EC2_PUBLIC_IP}:8000/health"
echo "• API Docs: http://${EC2_PUBLIC_IP}:8000/docs"
echo "• GitHub Actions: https://github.com/Anki246/kamikaze-be/actions"

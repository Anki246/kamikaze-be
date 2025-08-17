#!/bin/bash
# Monitor dev branch deployment status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Monitoring Dev Branch Deployment${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# Configuration
EC2_PUBLIC_IP="3.81.64.108"
GITHUB_REPO="https://github.com/Anki246/kamikaze-be"

echo -e "${YELLOW}📋 Deployment Information:${NC}"
echo "• Branch: dev"
echo "• Environment: development"
echo "• EC2 Instance: i-08bc5befe61de1a51"
echo "• Public IP: ${EC2_PUBLIC_IP}"
echo "• Database: AWS RDS (kmkz-database-new)"
echo ""

echo -e "${YELLOW}🔗 Important URLs:${NC}"
echo "• GitHub Actions: ${GITHUB_REPO}/actions"
echo "• Application: http://${EC2_PUBLIC_IP}:8000"
echo "• Health Check: http://${EC2_PUBLIC_IP}:8000/health"
echo "• API Docs: http://${EC2_PUBLIC_IP}:8000/docs"
echo ""

# Function to check application status
check_application() {
    echo -e "${YELLOW}🔍 Checking Application Status...${NC}"
    
    # Test basic connectivity
    if ping -c 3 ${EC2_PUBLIC_IP} > /dev/null 2>&1; then
        echo -e "${GREEN}✅ EC2 instance is reachable${NC}"
    else
        echo -e "${RED}❌ EC2 instance is not reachable${NC}"
        return 1
    fi
    
    # Test SSH port
    if nc -z -w5 ${EC2_PUBLIC_IP} 22 2>/dev/null; then
        echo -e "${GREEN}✅ SSH port (22) is accessible${NC}"
    else
        echo -e "${RED}❌ SSH port (22) is not accessible${NC}"
    fi
    
    # Test application port
    if nc -z -w5 ${EC2_PUBLIC_IP} 8000 2>/dev/null; then
        echo -e "${GREEN}✅ Application port (8000) is accessible${NC}"
        
        # Test health endpoint
        if curl -f -s http://${EC2_PUBLIC_IP}:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Application health check passed${NC}"
            
            # Get health response
            echo -e "${BLUE}📋 Health Response:${NC}"
            curl -s http://${EC2_PUBLIC_IP}:8000/health | python -m json.tool 2>/dev/null || curl -s http://${EC2_PUBLIC_IP}:8000/health
        else
            echo -e "${RED}❌ Application health check failed${NC}"
        fi
    else
        echo -e "${RED}❌ Application port (8000) is not accessible${NC}"
    fi
}

# Function to check GitHub Actions status
check_github_actions() {
    echo -e "${YELLOW}🔍 GitHub Actions Status...${NC}"
    echo "Please check the GitHub Actions page for detailed status:"
    echo "${GITHUB_REPO}/actions"
    echo ""
    echo "Look for the workflow: '🧪 Deploy to Dev Branch'"
    echo "Expected steps:"
    echo "  1. 🏗️ Build and Test"
    echo "  2. 🚀 Deploy to Dev Environment"
    echo "     - Setup SSH key"
    echo "     - Run database migration"
    echo "     - Deploy to EC2"
    echo "     - Health checks"
    echo "     - Smoke tests"
    echo "     - Database connection test"
}

# Function to show next steps
show_next_steps() {
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo ""
    echo "1. 🔍 Monitor GitHub Actions:"
    echo "   ${GITHUB_REPO}/actions"
    echo ""
    echo "2. ✅ If deployment succeeds:"
    echo "   • Test application: http://${EC2_PUBLIC_IP}:8000"
    echo "   • Check health: http://${EC2_PUBLIC_IP}:8000/health"
    echo "   • View API docs: http://${EC2_PUBLIC_IP}:8000/docs"
    echo "   • Verify RDS connection in logs"
    echo ""
    echo "3. ❌ If deployment fails:"
    echo "   • Check GitHub Actions logs for errors"
    echo "   • Verify GitHub secrets are configured in 'development' environment"
    echo "   • Check EC2 instance status"
    echo "   • Review migration logs"
    echo ""
    echo "4. 🚀 If dev deployment is successful:"
    echo "   • Merge dev branch to main for production deployment"
    echo "   • Monitor production deployment"
    echo ""
}

# Function to show required secrets
show_required_secrets() {
    echo -e "${YELLOW}🔐 Required GitHub Secrets (development environment):${NC}"
    echo ""
    echo "• EC2_SSH_PRIVATE_KEY - SSH private key for EC2 access"
    echo "• DB_HOST - RDS endpoint (e.g., kmkz-database-new.xyz.us-east-1.rds.amazonaws.com)"
    echo "• DB_PORT - Database port (usually 5432)"
    echo "• DB_NAME - Database name (e.g., kamikaze)"
    echo "• DB_USER - Database username"
    echo "• DB_PASSWORD - Database password"
    echo ""
    echo "Configure these at:"
    echo "${GITHUB_REPO}/settings/environments"
    echo ""
}

# Main execution
echo -e "${BLUE}🚀 Starting monitoring...${NC}"
echo ""

# Check if we can reach the application
check_application
echo ""

# Show GitHub Actions info
check_github_actions
echo ""

# Show required secrets
show_required_secrets

# Show next steps
show_next_steps

echo -e "${BLUE}🔄 Continuous Monitoring:${NC}"
echo "Run this script periodically to check deployment status:"
echo "./scripts/monitor-dev-deployment.sh"
echo ""

# Optional: Continuous monitoring loop
read -p "🤔 Do you want to start continuous monitoring? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🔄 Starting continuous monitoring (Ctrl+C to stop)...${NC}"
    echo ""
    
    while true; do
        echo -e "${BLUE}$(date): Checking application status...${NC}"
        check_application
        echo ""
        echo -e "${YELLOW}⏳ Waiting 30 seconds before next check...${NC}"
        sleep 30
        echo ""
    done
fi

echo -e "${GREEN}✨ Monitoring complete!${NC}"

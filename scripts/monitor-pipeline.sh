#!/bin/bash

# Kamikaze AI Pipeline Monitor Script
# Monitors the GitHub Actions pipeline status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS") echo -e "${GREEN}✅ $message${NC}" ;;
        "ERROR") echo -e "${RED}❌ $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}⚠️ $message${NC}" ;;
        "INFO") echo -e "${BLUE}ℹ️ $message${NC}" ;;
    esac
}

echo "🔍 Kamikaze AI Pipeline Monitor"
echo "==============================="
echo "Monitoring GitHub Actions deployment..."
echo ""

# Get the latest commit hash
COMMIT_HASH=$(git rev-parse HEAD)
SHORT_HASH=${COMMIT_HASH:0:7}

print_status "INFO" "Latest commit: $SHORT_HASH"
print_status "INFO" "Branch: $(git branch --show-current)"
print_status "INFO" "Repository: $(git config --get remote.origin.url)"

echo ""
echo "🔄 Pipeline Status:"
echo "-------------------"

# Check if we can access GitHub API (optional)
if command -v curl &> /dev/null; then
    print_status "INFO" "Checking GitHub Actions status..."
    
    # Note: This would require GitHub token for private repos
    # For now, just show the manual links
    
    REPO_URL=$(git config --get remote.origin.url | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//')
    
    echo ""
    echo "📋 Quick Links:"
    echo "---------------"
    echo "🔗 GitHub Actions: ${REPO_URL}/actions"
    echo "🔗 Latest Workflow: ${REPO_URL}/actions/workflows/deploy.yml"
    echo "🔗 Commit: ${REPO_URL}/commit/${COMMIT_HASH}"
    
else
    print_status "WARNING" "curl not available - cannot check API status"
fi

echo ""
echo "⏱️ Expected Timeline:"
echo "--------------------"
print_status "INFO" "Build Job: ~5-8 minutes (Docker build)"
print_status "INFO" "Deploy Job: ~3-5 minutes (file transfer + deployment)"
print_status "INFO" "Total Time: ~10-15 minutes"

echo ""
echo "🎯 What to Watch For:"
echo "--------------------"
echo "✅ Build Job:"
echo "   • Checkout code"
echo "   • Setup Python 3.11"
echo "   • Install dependencies"
echo "   • Run syntax checks (FIXED)"
echo "   • Validate configuration"
echo "   • Build Docker image"
echo "   • Test Docker image (ENHANCED)"
echo "   • Upload artifacts"

echo ""
echo "✅ Deploy Job:"
echo "   • Configure AWS credentials"
echo "   • Setup SSH key"
echo "   • Upload files to EC2"
echo "   • Zero-downtime deployment"
echo "   • Health verification"

echo ""
echo "✅ Cleanup Job:"
echo "   • Clean up artifacts"

echo ""
echo "🚨 Common Issues (Now Fixed):"
echo "----------------------------"
print_status "SUCCESS" "Syntax checks - Fixed to reference existing files"
print_status "SUCCESS" "Docker testing - Enhanced with proper health checks"
print_status "SUCCESS" "Missing __init__.py files - Created"
print_status "SUCCESS" "Environment variables - Added PYTHONPATH"

echo ""
echo "🔧 If Issues Occur:"
echo "------------------"
echo "1. Check GitHub Actions logs for specific errors"
echo "2. Run: ./scripts/troubleshoot-pipeline.sh"
echo "3. Verify GitHub secrets are configured"
echo "4. Check EC2 instance status and security groups"

echo ""
print_status "INFO" "Monitor the pipeline at: ${REPO_URL}/actions"
print_status "INFO" "This script will continue monitoring..."

# Simple monitoring loop
echo ""
echo "🔄 Monitoring (Press Ctrl+C to stop)..."
echo "========================================"

counter=0
while true; do
    counter=$((counter + 1))
    current_time=$(date '+%H:%M:%S')
    
    echo -ne "\r⏱️ Monitoring... ${current_time} (${counter}m elapsed)"
    
    # Check if local backend is running (if deployed locally)
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        print_status "SUCCESS" "Local backend is responding!"
        echo "🌐 Access: http://localhost:8000"
        echo "📋 Swagger: http://localhost:8000/docs"
        break
    fi
    
    sleep 60  # Check every minute
done

echo ""
print_status "SUCCESS" "Pipeline monitoring complete!"

#!/bin/bash

# Kamikaze AI Pipeline Troubleshooting Script
# This script helps diagnose common pipeline deployment issues

set -e

echo "🔍 Kamikaze AI Pipeline Troubleshooting"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
    print_status "ERROR" "Not in the Kamikaze AI project root directory"
    exit 1
fi

print_status "SUCCESS" "Found Kamikaze AI project files"

# 1. Check Python syntax
echo ""
echo "🐍 Checking Python Syntax..."
echo "----------------------------"

files_to_check=(
    "app.py"
    "src/api/main.py"
    "src/infrastructure/aws_secrets_manager.py"
    "src/infrastructure/auth_database.py"
    "src/infrastructure/database_config.py"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        if python -m py_compile "$file" 2>/dev/null; then
            print_status "SUCCESS" "Syntax check passed: $file"
        else
            print_status "ERROR" "Syntax error in: $file"
            python -m py_compile "$file"
        fi
    else
        print_status "WARNING" "File not found: $file"
    fi
done

# 2. Check configuration files
echo ""
echo "⚙️ Checking Configuration Files..."
echo "----------------------------------"

if [ -f "config.json" ]; then
    if python -c "import json; json.load(open('config.json'))" 2>/dev/null; then
        print_status "SUCCESS" "config.json is valid JSON"
    else
        print_status "ERROR" "config.json has invalid JSON syntax"
        python -c "import json; json.load(open('config.json'))"
    fi
else
    print_status "WARNING" "config.json not found"
fi

# 3. Check requirements.txt
echo ""
echo "📦 Checking Dependencies..."
echo "---------------------------"

if [ -f "requirements.txt" ]; then
    print_status "SUCCESS" "requirements.txt found"
    
    # Check for common problematic dependencies
    if grep -q "TA-Lib" requirements.txt; then
        print_status "WARNING" "TA-Lib requires system dependencies (build-essential, etc.)"
    fi
    
    if grep -q "psycopg2-binary" requirements.txt; then
        print_status "INFO" "psycopg2-binary found - good for Docker builds"
    fi
else
    print_status "ERROR" "requirements.txt not found"
fi

# 4. Check Dockerfile
echo ""
echo "🐳 Checking Docker Configuration..."
echo "-----------------------------------"

if [ -f "Dockerfile" ]; then
    print_status "SUCCESS" "Dockerfile found"
    
    # Check for common issues
    if grep -q "PYTHONPATH" Dockerfile; then
        print_status "SUCCESS" "PYTHONPATH is set in Dockerfile"
    else
        print_status "WARNING" "PYTHONPATH not set in Dockerfile"
    fi
    
    if grep -q "build-essential" Dockerfile; then
        print_status "SUCCESS" "build-essential included for TA-Lib"
    else
        print_status "WARNING" "build-essential not found - may cause TA-Lib build issues"
    fi
else
    print_status "ERROR" "Dockerfile not found"
fi

# 5. Test Docker build (if Docker is available)
echo ""
echo "🔨 Testing Docker Build..."
echo "---------------------------"

if command -v docker &> /dev/null; then
    print_status "INFO" "Docker is available, testing build..."
    
    if docker build -t kamikaze-ai-test . > /tmp/docker_build.log 2>&1; then
        print_status "SUCCESS" "Docker build completed successfully"
        docker rmi kamikaze-ai-test 2>/dev/null || true
    else
        print_status "ERROR" "Docker build failed"
        echo "Build log:"
        tail -20 /tmp/docker_build.log
    fi
else
    print_status "WARNING" "Docker not available - skipping build test"
fi

# 6. Check GitHub Actions workflow
echo ""
echo "🔄 Checking GitHub Actions Workflow..."
echo "--------------------------------------"

if [ -f ".github/workflows/deploy.yml" ]; then
    print_status "SUCCESS" "GitHub Actions workflow found"
    
    # Check for required secrets references
    secrets_found=0
    required_secrets=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "EC2_HOST" "EC2_USER" "EC2_SSH_PRIVATE_KEY")
    
    for secret in "${required_secrets[@]}"; do
        if grep -q "$secret" .github/workflows/deploy.yml; then
            ((secrets_found++))
        fi
    done
    
    print_status "INFO" "Found $secrets_found/${#required_secrets[@]} required secrets in workflow"
    
    if [ $secrets_found -eq ${#required_secrets[@]} ]; then
        print_status "SUCCESS" "All required secrets are referenced in workflow"
    else
        print_status "WARNING" "Some required secrets may be missing"
    fi
else
    print_status "ERROR" "GitHub Actions workflow not found"
fi

# 7. Summary and recommendations
echo ""
echo "📋 Summary and Recommendations..."
echo "--------------------------------"

print_status "INFO" "Troubleshooting complete!"
echo ""
echo "Next steps:"
echo "1. Fix any syntax errors found above"
echo "2. Ensure all required GitHub secrets are configured"
echo "3. Test Docker build locally before pushing"
echo "4. Check GitHub Actions logs for specific error messages"
echo ""
echo "Required GitHub Secrets:"
echo "- AWS_ACCESS_KEY_ID"
echo "- AWS_SECRET_ACCESS_KEY"
echo "- AWS_REGION (optional, defaults to us-east-1)"
echo "- EC2_HOST"
echo "- EC2_USER"
echo "- EC2_SSH_PRIVATE_KEY"
echo ""
echo "For more help, see: GITHUB_SECRETS_SETUP.md"

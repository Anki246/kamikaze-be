#!/bin/bash

# Kamikaze AI Pipeline Quick Fix Script
# Automatically fixes common pipeline deployment issues

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

echo "🔧 Kamikaze AI Pipeline Quick Fix"
echo "================================="

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
    print_status "ERROR" "Not in the Kamikaze AI project root directory"
    exit 1
fi

# 1. Fix Python path issues
echo ""
echo "🐍 Fixing Python Path Issues..."
echo "-------------------------------"

# Ensure __init__.py files exist
init_files=(
    "src/__init__.py"
    "src/api/__init__.py"
    "src/infrastructure/__init__.py"
    "src/agents/__init__.py"
    "src/agents/fluxtrader/__init__.py"
)

for init_file in "${init_files[@]}"; do
    if [ ! -f "$init_file" ]; then
        mkdir -p "$(dirname "$init_file")"
        touch "$init_file"
        print_status "SUCCESS" "Created missing $init_file"
    fi
done

# 2. Fix Docker build issues
echo ""
echo "🐳 Fixing Docker Configuration..."
echo "--------------------------------"

# Check if Dockerfile has proper PYTHONPATH
if ! grep -q "PYTHONPATH=/app/src" Dockerfile; then
    print_status "WARNING" "PYTHONPATH not properly set in Dockerfile"
    echo "Consider adding: ENV PYTHONPATH=/app/src"
fi

# 3. Fix requirements.txt issues
echo ""
echo "📦 Fixing Dependencies..."
echo "------------------------"

# Check for common dependency issues
if grep -q "^TA-Lib" requirements.txt; then
    print_status "INFO" "TA-Lib found - ensure build-essential is in Dockerfile"
fi

# Add missing dependencies if needed
missing_deps=()

if ! grep -q "fastapi" requirements.txt; then
    missing_deps+=("fastapi>=0.104.0")
fi

if ! grep -q "uvicorn" requirements.txt; then
    missing_deps+=("uvicorn>=0.24.0")
fi

if ! grep -q "asyncpg" requirements.txt; then
    missing_deps+=("asyncpg>=0.29.0")
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    print_status "WARNING" "Missing dependencies detected"
    echo "Consider adding:"
    for dep in "${missing_deps[@]}"; do
        echo "  - $dep"
    done
fi

# 4. Fix GitHub Actions workflow issues
echo ""
echo "🔄 Fixing GitHub Actions Workflow..."
echo "-----------------------------------"

workflow_file=".github/workflows/deploy.yml"

if [ -f "$workflow_file" ]; then
    # Check for common issues and suggest fixes
    
    # Check if syntax check files exist
    if grep -q "src/infrastructure/config_loader.py" "$workflow_file"; then
        if [ ! -f "src/infrastructure/config_loader.py" ]; then
            print_status "WARNING" "Workflow references missing config_loader.py"
            echo "Consider updating workflow to check existing files"
        fi
    fi
    
    # Check for proper environment variables
    if ! grep -q "PYTHONPATH" "$workflow_file"; then
        print_status "WARNING" "PYTHONPATH not set in workflow Docker run"
        echo "Consider adding: -e PYTHONPATH=/app/src"
    fi
    
    print_status "SUCCESS" "GitHub Actions workflow checked"
else
    print_status "ERROR" "GitHub Actions workflow not found"
fi

# 5. Fix configuration issues
echo ""
echo "⚙️ Fixing Configuration..."
echo "-------------------------"

# Validate config.json
if [ -f "config.json" ]; then
    if python -c "import json; json.load(open('config.json'))" 2>/dev/null; then
        print_status "SUCCESS" "config.json is valid"
    else
        print_status "ERROR" "config.json has syntax errors"
        echo "Run: python -c \"import json; json.load(open('config.json'))\""
    fi
fi

# 6. Create missing scripts directory
echo ""
echo "📁 Fixing Directory Structure..."
echo "-------------------------------"

if [ ! -d "scripts" ]; then
    mkdir -p scripts
    print_status "SUCCESS" "Created scripts directory"
fi

if [ ! -d "logs" ]; then
    mkdir -p logs
    print_status "SUCCESS" "Created logs directory"
fi

# 7. Fix permissions
echo ""
echo "🔐 Fixing Permissions..."
echo "-----------------------"

# Make scripts executable
if [ -d "scripts" ]; then
    find scripts -name "*.sh" -exec chmod +x {} \;
    print_status "SUCCESS" "Made shell scripts executable"
fi

# 8. Generate .dockerignore if missing
echo ""
echo "🚫 Fixing Docker Ignore..."
echo "-------------------------"

if [ ! -f ".dockerignore" ]; then
    cat > .dockerignore << 'EOF'
.git
.github
node_modules
__pycache__
*.pyc
.pytest_cache
logs
.env
.env.local
.DS_Store
*.log
.vscode
.idea
README.md
*.md
EOF
    print_status "SUCCESS" "Created .dockerignore file"
fi

# 9. Summary and next steps
echo ""
echo "📋 Quick Fix Summary"
echo "==================="

print_status "SUCCESS" "Pipeline quick fix completed!"

echo ""
echo "Next steps:"
echo "1. Test the fixes: ./scripts/troubleshoot-pipeline.sh"
echo "2. Test Docker build: docker build -t kamikaze-ai-test ."
echo "3. Commit and push changes to trigger pipeline"
echo "4. Monitor GitHub Actions for successful deployment"

echo ""
echo "If issues persist:"
echo "- Check GitHub Actions logs for specific errors"
echo "- Verify all GitHub secrets are configured"
echo "- Test SSH connection to EC2 instance"
echo "- Check EC2 security groups and instance status"

echo ""
print_status "INFO" "Pipeline quick fix complete!"

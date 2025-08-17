#!/bin/bash
# Verify code quality and formatting compliance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Code Quality Verification${NC}"
echo -e "${BLUE}===========================${NC}"
echo ""

# Check if required tools are installed
echo -e "${YELLOW}📦 Checking required tools...${NC}"

if ! command -v black &> /dev/null; then
    echo -e "${RED}❌ Black not found. Installing...${NC}"
    pip install black==23.3.0
else
    echo -e "${GREEN}✅ Black found${NC}"
fi

if ! command -v isort &> /dev/null; then
    echo -e "${RED}❌ isort not found. Installing...${NC}"
    pip install isort==5.11.5
else
    echo -e "${GREEN}✅ isort found${NC}"
fi

echo ""

# Run Black check
echo -e "${YELLOW}🎨 Running Black formatting check...${NC}"
if black --check --diff . > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Black formatting: PASSED${NC}"
else
    echo -e "${RED}❌ Black formatting: FAILED${NC}"
    echo -e "${YELLOW}💡 Running Black to show differences:${NC}"
    black --check --diff .
    echo ""
    echo -e "${YELLOW}💡 To fix, run: black .${NC}"
    exit 1
fi

# Run isort check
echo -e "${YELLOW}📚 Running isort import sorting check...${NC}"
if isort --check-only --diff . > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Import sorting: PASSED${NC}"
else
    echo -e "${RED}❌ Import sorting: FAILED${NC}"
    echo -e "${YELLOW}💡 Running isort to show differences:${NC}"
    isort --check-only --diff .
    echo ""
    echo -e "${YELLOW}💡 To fix, run: isort .${NC}"
    exit 1
fi

# Check Python syntax
echo -e "${YELLOW}🐍 Running Python syntax check...${NC}"
syntax_errors=0

# Check main files
for file in src/api/main.py src/infrastructure/database_config.py scripts/migrate-to-rds.py; do
    if [ -f "$file" ]; then
        if python -m py_compile "$file" 2>/dev/null; then
            echo -e "${GREEN}✅ $file: Syntax OK${NC}"
        else
            echo -e "${RED}❌ $file: Syntax ERROR${NC}"
            python -m py_compile "$file"
            syntax_errors=$((syntax_errors + 1))
        fi
    fi
done

if [ $syntax_errors -gt 0 ]; then
    echo -e "${RED}❌ Found $syntax_errors syntax errors${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Python syntax: PASSED${NC}"
fi

# Check import structure
echo -e "${YELLOW}📦 Checking critical imports...${NC}"
cd src && python -c "
import sys
import os

try:
    from infrastructure.database_config import DatabaseConfig
    print('✅ DatabaseConfig import: OK')

    # Test database config creation
    config = DatabaseConfig()
    print('✅ DatabaseConfig instantiation: OK')

    from infrastructure.auth_database import get_db_config
    print('✅ Auth database import: OK')

    # Test basic FastAPI import (without relative imports)
    import fastapi
    print('✅ FastAPI library import: OK')

    print('✅ All critical imports: PASSED')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" && cd ..

echo ""
echo -e "${GREEN}🎉 All code quality checks passed!${NC}"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "• ✅ Black formatting compliance"
echo "• ✅ Import sorting compliance"
echo "• ✅ Python syntax validation"
echo "• ✅ Critical imports working"
echo ""
echo -e "${BLUE}🚀 Ready for CI/CD pipeline!${NC}"

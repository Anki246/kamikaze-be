#!/bin/bash
# Setup script for RDS migration
# Helps configure environment variables and run migration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 RDS Migration Setup for Kamikaze-be${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if running in GitHub Actions
if [ "${GITHUB_ACTIONS}" = "true" ]; then
    echo -e "${GREEN}🤖 Running in GitHub Actions${NC}"
    echo -e "${BLUE}RDS Host: ${DB_HOST}${NC}"
    echo -e "${BLUE}RDS Database: ${DB_NAME}${NC}"
    echo -e "${BLUE}RDS User: ${DB_USER}${NC}"
    
    # Run migration
    echo -e "${YELLOW}🔄 Starting migration...${NC}"
    python scripts/migrate-to-rds.py
    
else
    echo -e "${YELLOW}🖥️  Running locally${NC}"
    echo ""
    echo -e "${YELLOW}📋 To run migration locally, you need to set these environment variables:${NC}"
    echo ""
    echo -e "${BLUE}# RDS Database (Target)${NC}"
    echo "export DB_HOST='your-rds-endpoint.rds.amazonaws.com'"
    echo "export DB_PORT='5432'"
    echo "export DB_NAME='kamikaze'"
    echo "export DB_USER='your-rds-username'"
    echo "export DB_PASSWORD='your-rds-password'"
    echo ""
    echo -e "${BLUE}# Local Database (Source) - Optional overrides${NC}"
    echo "export LOCAL_DB_NAME='kamikaze'"
    echo "export LOCAL_DB_USER='postgres'"
    echo "export LOCAL_DB_PASSWORD='admin2025'"
    echo ""
    echo -e "${YELLOW}📝 Example usage:${NC}"
    echo "export DB_HOST='kmkz-database-new.xyz.us-east-1.rds.amazonaws.com'"
    echo "export DB_USER='postgres'"
    echo "export DB_PASSWORD='your-secure-password'"
    echo "python scripts/migrate-to-rds.py"
    echo ""
    
    # Check if RDS variables are set
    if [ -n "${DB_HOST}" ] && [ -n "${DB_USER}" ] && [ -n "${DB_PASSWORD}" ]; then
        echo -e "${GREEN}✅ RDS credentials detected${NC}"
        echo -e "${BLUE}RDS Host: ${DB_HOST}${NC}"
        echo -e "${BLUE}RDS Database: ${DB_NAME:-kamikaze}${NC}"
        echo -e "${BLUE}RDS User: ${DB_USER}${NC}"
        echo ""
        
        read -p "🤔 Do you want to run the migration now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}🔄 Starting migration...${NC}"
            python scripts/migrate-to-rds.py
        else
            echo -e "${BLUE}👍 Migration skipped${NC}"
        fi
    else
        echo -e "${RED}❌ RDS credentials not set${NC}"
        echo -e "${YELLOW}💡 Set the environment variables above and run this script again${NC}"
    fi
fi

echo ""
echo -e "${BLUE}🔗 Useful Commands:${NC}"
echo "• Test RDS connection: python -c \"import asyncio; from scripts.migrate_to_rds import DatabaseMigrator; asyncio.run(DatabaseMigrator().connect_databases())\""
echo "• View migration logs: ls -la migration_*.log"
echo "• GitHub Actions: https://github.com/Anki246/kamikaze-be/actions"
echo ""
echo -e "${GREEN}✨ Setup complete!${NC}"

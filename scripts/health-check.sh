#!/bin/bash
# FluxTrader Backend - Health Check Script
# Performs comprehensive health checks on the deployed application

set -e

# Configuration
EC2_PUBLIC_IP="34.238.167.174"
APP_PORT="8000"
CONTAINER_NAME="fluxtrader-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏥 FluxTrader Backend Health Check${NC}"
echo -e "${BLUE}Target: ${EC2_PUBLIC_IP}:${APP_PORT}${NC}"

# Function to check HTTP endpoint
check_endpoint() {
    local endpoint=$1
    local description=$2
    
    echo -e "${YELLOW}🔍 Checking ${description}...${NC}"
    
    if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}${endpoint}" > /dev/null; then
        echo -e "${GREEN}✅ ${description} - OK${NC}"
        return 0
    else
        echo -e "${RED}❌ ${description} - FAILED${NC}"
        return 1
    fi
}

# Function to check endpoint with response
check_endpoint_with_response() {
    local endpoint=$1
    local description=$2
    
    echo -e "${YELLOW}🔍 Checking ${description}...${NC}"
    
    response=$(curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}${endpoint}" 2>/dev/null || echo "FAILED")
    
    if [ "$response" != "FAILED" ]; then
        echo -e "${GREEN}✅ ${description} - OK${NC}"
        echo -e "${BLUE}Response: ${response}${NC}"
        return 0
    else
        echo -e "${RED}❌ ${description} - FAILED${NC}"
        return 1
    fi
}

# Check if EC2 is accessible
echo -e "${YELLOW}📡 Checking EC2 connectivity...${NC}"
if ping -c 1 -W 5 ${EC2_PUBLIC_IP} > /dev/null 2>&1; then
    echo -e "${GREEN}✅ EC2 instance is reachable${NC}"
else
    echo -e "${RED}❌ EC2 instance is not reachable${NC}"
    exit 1
fi

# Check if application port is open
echo -e "${YELLOW}🔌 Checking application port...${NC}"
if nc -z -w5 ${EC2_PUBLIC_IP} ${APP_PORT} 2>/dev/null; then
    echo -e "${GREEN}✅ Port ${APP_PORT} is open${NC}"
else
    echo -e "${RED}❌ Port ${APP_PORT} is not accessible${NC}"
    exit 1
fi

# Health check endpoints
health_passed=0
total_checks=0

# Basic health check
total_checks=$((total_checks + 1))
if check_endpoint_with_response "/health" "Basic Health Check"; then
    health_passed=$((health_passed + 1))
fi

# API documentation
total_checks=$((total_checks + 1))
if check_endpoint "/docs" "API Documentation"; then
    health_passed=$((health_passed + 1))
fi

# OpenAPI schema
total_checks=$((total_checks + 1))
if check_endpoint "/openapi.json" "OpenAPI Schema"; then
    health_passed=$((health_passed + 1))
fi

# Database connectivity (if endpoint exists)
total_checks=$((total_checks + 1))
if check_endpoint_with_response "/health/database" "Database Connectivity"; then
    health_passed=$((health_passed + 1))
else
    echo -e "${YELLOW}⚠️  Database health endpoint may not be implemented${NC}"
fi

# AWS Secrets Manager connectivity (if endpoint exists)
total_checks=$((total_checks + 1))
if check_endpoint_with_response "/health/aws" "AWS Services Connectivity"; then
    health_passed=$((health_passed + 1))
else
    echo -e "${YELLOW}⚠️  AWS health endpoint may not be implemented${NC}"
fi

# Summary
echo -e "\n${BLUE}📊 Health Check Summary${NC}"
echo -e "Passed: ${health_passed}/${total_checks} checks"

if [ $health_passed -eq $total_checks ]; then
    echo -e "${GREEN}🎉 All health checks passed!${NC}"
    exit 0
elif [ $health_passed -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Some health checks failed, but basic functionality is working${NC}"
    exit 0
else
    echo -e "${RED}❌ All health checks failed - application may not be running properly${NC}"
    exit 1
fi

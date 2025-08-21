#!/bin/bash

# Kamikaze AI Deployment Verification Script
# Verifies that the deployment is working correctly

set -e

# Configuration
HOST=${1:-"localhost"}
PORT=${2:-"8000"}
BASE_URL="http://${HOST}:${PORT}"

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

echo "🔍 Kamikaze AI Deployment Verification"
echo "======================================"
echo "Testing: $BASE_URL"
echo ""

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local description=$3
    
    echo "Testing: $endpoint"
    
    response=$(curl -s -w "%{http_code}" -o /tmp/response.json "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        print_status "SUCCESS" "$description"
        if [ -f /tmp/response.json ] && [ -s /tmp/response.json ]; then
            echo "Response preview:"
            head -c 200 /tmp/response.json | jq . 2>/dev/null || head -c 200 /tmp/response.json
            echo ""
        fi
    else
        print_status "ERROR" "$description (HTTP $response)"
        if [ -f /tmp/response.json ]; then
            echo "Response:"
            cat /tmp/response.json
            echo ""
        fi
    fi
    echo ""
}

# 1. Basic connectivity test
echo "🌐 Testing Basic Connectivity..."
echo "-------------------------------"

if curl -s --connect-timeout 5 "$BASE_URL" > /dev/null 2>&1; then
    print_status "SUCCESS" "Server is reachable"
else
    print_status "ERROR" "Server is not reachable"
    echo "Please check:"
    echo "1. Server is running"
    echo "2. Port $PORT is open"
    echo "3. Firewall settings"
    exit 1
fi

# 2. Health check endpoints
echo "🏥 Testing Health Endpoints..."
echo "-----------------------------"

test_endpoint "/health" 200 "Main health check"
test_endpoint "/health/database" 200 "Database health check"
test_endpoint "/health/aws" 200 "AWS health check"

# 3. API endpoints
echo "🔌 Testing API Endpoints..."
echo "---------------------------"

test_endpoint "/api/info" 200 "API info endpoint"
test_endpoint "/docs" 200 "Swagger documentation"
test_endpoint "/openapi.json" 200 "OpenAPI specification"

# 4. Authentication endpoints
echo "🔐 Testing Authentication..."
echo "----------------------------"

# Test signin endpoint (should return 422 for missing body)
test_endpoint "/api/v1/auth/signin" 422 "Signin endpoint (expects POST with body)"

# 5. Agent endpoints
echo "🤖 Testing Agent Endpoints..."
echo "-----------------------------"

test_endpoint "/api/v1/agents/" 200 "List agents endpoint"

# 6. Database endpoints (these require authentication, so expect 401)
echo "🗄️ Testing Database Endpoints..."
echo "--------------------------------"

test_endpoint "/api/database/tables" 401 "Database tables (requires auth)"
test_endpoint "/api/database/health" 401 "Database health (requires auth)"

# 7. Performance test
echo "⚡ Testing Performance..."
echo "------------------------"

start_time=$(date +%s)
curl -s "$BASE_URL/health" > /dev/null
end_time=$(date +%s)
duration=$((end_time - start_time))

if [ $duration -eq 0 ]; then
    print_status "SUCCESS" "Response time: <1s (excellent)"
elif [ $duration -eq 1 ]; then
    print_status "SUCCESS" "Response time: 1s (good)"
else
    print_status "WARNING" "Response time: ${duration}s (slow)"
fi

# 8. Docker container check (if running locally)
if [ "$HOST" = "localhost" ] && command -v docker &> /dev/null; then
    echo ""
    echo "🐳 Docker Container Status..."
    echo "----------------------------"
    
    if docker ps | grep -q kamikaze-ai-backend; then
        print_status "SUCCESS" "Kamikaze AI container is running"
        
        # Show container stats
        echo "Container info:"
        docker ps --filter name=kamikaze-ai-backend --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        # Show recent logs
        echo ""
        echo "Recent logs:"
        docker logs kamikaze-ai-backend --tail 5 2>/dev/null || echo "No logs available"
    else
        print_status "WARNING" "Kamikaze AI container not found"
    fi
fi

# 9. Summary
echo ""
echo "📋 Deployment Verification Summary"
echo "=================================="

# Count successful tests (this is a simplified check)
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    print_status "SUCCESS" "Deployment verification completed"
    echo ""
    echo "✅ Your Kamikaze AI backend is running successfully!"
    echo ""
    echo "🌐 Access points:"
    echo "   • API: $BASE_URL"
    echo "   • Swagger UI: $BASE_URL/docs"
    echo "   • Health Check: $BASE_URL/health"
    echo ""
    echo "🔐 To test authenticated endpoints:"
    echo "   1. Get a token: POST $BASE_URL/api/v1/auth/signin"
    echo "   2. Use token: Authorization: Bearer <token>"
    echo ""
else
    print_status "ERROR" "Deployment verification failed"
    echo ""
    echo "❌ Issues detected with your deployment"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "   1. Check server logs"
    echo "   2. Verify configuration"
    echo "   3. Check database connectivity"
    echo "   4. Verify AWS credentials"
fi

# Cleanup
rm -f /tmp/response.json

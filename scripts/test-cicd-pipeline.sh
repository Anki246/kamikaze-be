#!/bin/bash
# FluxTrader CI/CD Pipeline Test Script
# This script tests the complete CI/CD pipeline end-to-end

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("$1")
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to test AWS connectivity and permissions
test_aws_connectivity() {
    print_header "Testing AWS Connectivity and Permissions"
    
    # Test basic connectivity
    if aws sts get-caller-identity &> /dev/null; then
        print_success "AWS connectivity verified"
    else
        print_failure "AWS connectivity failed"
        return 1
    fi
    
    # Test EC2 permissions
    if aws ec2 describe-regions --max-items 1 &> /dev/null; then
        print_success "EC2 permissions verified"
    else
        print_failure "EC2 permissions failed"
    fi
    
    # Test RDS permissions
    if aws rds describe-db-instances --max-items 1 &> /dev/null; then
        print_success "RDS permissions verified"
    else
        print_failure "RDS permissions failed"
    fi
    
    # Test Secrets Manager permissions
    if aws secretsmanager list-secrets --max-items 1 &> /dev/null; then
        print_success "Secrets Manager permissions verified"
    else
        print_failure "Secrets Manager permissions failed"
    fi
    
    # Test CloudFormation permissions
    if aws cloudformation list-stacks --max-items 1 &> /dev/null; then
        print_success "CloudFormation permissions verified"
    else
        print_failure "CloudFormation permissions failed"
    fi
    
    # Test IAM permissions
    if aws iam get-user &> /dev/null; then
        print_success "IAM permissions verified"
    else
        print_failure "IAM permissions failed"
    fi
}

# Function to test infrastructure deployment
test_infrastructure_deployment() {
    print_header "Testing Infrastructure Deployment"
    
    local stack_name="fluxtrader-staging"
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$stack_name" &> /dev/null; then
        print_info "CloudFormation stack exists: $stack_name"
        
        # Check stack status
        local stack_status=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --query 'Stacks[0].StackStatus' \
            --output text)
        
        if [[ "$stack_status" == "CREATE_COMPLETE" || "$stack_status" == "UPDATE_COMPLETE" ]]; then
            print_success "CloudFormation stack is in good state: $stack_status"
        else
            print_failure "CloudFormation stack is in bad state: $stack_status"
        fi
        
        # Test stack outputs
        local outputs=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --query 'Stacks[0].Outputs' \
            --output json)
        
        if echo "$outputs" | jq -e '.[] | select(.OutputKey=="InstanceId")' &> /dev/null; then
            print_success "EC2 Instance output found"
        else
            print_failure "EC2 Instance output missing"
        fi
        
        if echo "$outputs" | jq -e '.[] | select(.OutputKey=="DatabaseEndpoint")' &> /dev/null; then
            print_success "RDS Database output found"
        else
            print_failure "RDS Database output missing"
        fi
        
    else
        print_warning "CloudFormation stack does not exist: $stack_name"
        print_info "Run infrastructure deployment first:"
        print_info "./scripts/deploy-infrastructure.sh --environment staging --tool cloudformation --key-pair your-key --password your-password"
    fi
}

# Function to test EC2 instance
test_ec2_instance() {
    print_header "Testing EC2 Instance"
    
    local stack_name="fluxtrader-staging"
    
    # Get instance ID from CloudFormation
    local instance_id=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text 2>/dev/null)
    
    if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
        print_failure "Could not get EC2 instance ID from CloudFormation"
        return 1
    fi
    
    print_info "Testing EC2 instance: $instance_id"
    
    # Check instance state
    local instance_state=$(aws ec2 describe-instances \
        --instance-ids "$instance_id" \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text)
    
    if [[ "$instance_state" == "running" ]]; then
        print_success "EC2 instance is running"
    else
        print_failure "EC2 instance is not running: $instance_state"
    fi
    
    # Get public IP
    local public_ip=$(aws ec2 describe-instances \
        --instance-ids "$instance_id" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    if [[ -n "$public_ip" && "$public_ip" != "None" ]]; then
        print_success "EC2 instance has public IP: $public_ip"
        
        # Test connectivity (ping)
        if ping -c 1 -W 5 "$public_ip" &> /dev/null; then
            print_success "EC2 instance is reachable via ping"
        else
            print_warning "EC2 instance is not reachable via ping (may be normal)"
        fi
        
        # Test application health endpoint
        print_info "Testing application health endpoint..."
        if curl -f --connect-timeout 10 --max-time 30 "http://$public_ip:8000/health" &> /dev/null; then
            print_success "Application health endpoint is responding"
        else
            print_failure "Application health endpoint is not responding"
        fi
        
        # Test API documentation endpoint
        if curl -f --connect-timeout 10 --max-time 30 "http://$public_ip:8000/docs" &> /dev/null; then
            print_success "API documentation endpoint is responding"
        else
            print_failure "API documentation endpoint is not responding"
        fi
        
    else
        print_failure "EC2 instance does not have a public IP"
    fi
}

# Function to test RDS database
test_rds_database() {
    print_header "Testing RDS Database"
    
    local db_identifier="fluxtrader-staging"
    
    # Check if RDS instance exists
    if aws rds describe-db-instances --db-instance-identifier "$db_identifier" &> /dev/null; then
        print_success "RDS instance exists: $db_identifier"
        
        # Check RDS status
        local db_status=$(aws rds describe-db-instances \
            --db-instance-identifier "$db_identifier" \
            --query 'DBInstances[0].DBInstanceStatus' \
            --output text)
        
        if [[ "$db_status" == "available" ]]; then
            print_success "RDS instance is available"
        else
            print_failure "RDS instance is not available: $db_status"
        fi
        
        # Get RDS endpoint
        local db_endpoint=$(aws rds describe-db-instances \
            --db-instance-identifier "$db_identifier" \
            --query 'DBInstances[0].Endpoint.Address' \
            --output text)
        
        if [[ -n "$db_endpoint" && "$db_endpoint" != "None" ]]; then
            print_success "RDS endpoint available: $db_endpoint"
        else
            print_failure "RDS endpoint not available"
        fi
        
    else
        print_failure "RDS instance does not exist: $db_identifier"
    fi
}

# Function to test Secrets Manager
test_secrets_manager() {
    print_header "Testing AWS Secrets Manager"
    
    local secrets=(
        "fluxtrader/staging/database/main"
        "fluxtrader/staging/trading/api-keys"
        "fluxtrader/staging/application/secrets"
    )
    
    for secret in "${secrets[@]}"; do
        if aws secretsmanager describe-secret --secret-id "$secret" &> /dev/null; then
            print_success "Secret exists: $secret"
            
            # Test secret retrieval
            if aws secretsmanager get-secret-value --secret-id "$secret" &> /dev/null; then
                print_success "Secret is retrievable: $secret"
            else
                print_failure "Secret is not retrievable: $secret"
            fi
        else
            print_failure "Secret does not exist: $secret"
        fi
    done
}

# Function to test local application
test_local_application() {
    print_header "Testing Local Application"
    
    # Test Python imports
    if python3 -c "import sys; sys.path.insert(0, 'src'); from agents.fluxtrader.config import ConfigManager; print('✅ Config import successful')" 2>/dev/null; then
        print_success "FluxTrader config import works"
    else
        print_failure "FluxTrader config import failed"
    fi
    
    # Test AWS Secrets Manager integration
    if python3 -c "import sys; sys.path.insert(0, 'src'); from infrastructure.aws_secrets_manager import SecretsManager; print('✅ AWS Secrets Manager import successful')" 2>/dev/null; then
        print_success "AWS Secrets Manager integration import works"
    else
        print_failure "AWS Secrets Manager integration import failed"
    fi
    
    # Test MCP server imports
    if python3 -c "import sys; sys.path.insert(0, 'src'); from mcp_servers.binance_fastmcp_server import *; print('✅ MCP server import successful')" 2>/dev/null; then
        print_success "MCP server import works"
    else
        print_failure "MCP server import failed"
    fi
}

# Function to test GitHub Actions workflow files
test_github_workflows() {
    print_header "Testing GitHub Actions Workflow Files"
    
    local workflows=(
        ".github/workflows/ci-enhanced.yml"
        ".github/workflows/cd-staging-aws.yml"
        ".github/workflows/cd-production-aws.yml"
        ".github/workflows/security-scan.yml"
    )
    
    for workflow in "${workflows[@]}"; do
        if [[ -f "$workflow" ]]; then
            print_success "Workflow file exists: $workflow"
            
            # Basic YAML syntax check
            if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
                print_success "Workflow YAML syntax is valid: $workflow"
            else
                print_failure "Workflow YAML syntax is invalid: $workflow"
            fi
        else
            print_failure "Workflow file missing: $workflow"
        fi
    done
}

# Function to test Docker build
test_docker_build() {
    print_header "Testing Docker Build"
    
    if command -v docker &> /dev/null; then
        print_info "Testing Docker build..."
        
        if docker build -t fluxtrader:test . &> /dev/null; then
            print_success "Docker build successful"
            
            # Clean up test image
            docker rmi fluxtrader:test &> /dev/null || true
        else
            print_failure "Docker build failed"
        fi
    else
        print_warning "Docker not installed, skipping Docker build test"
    fi
}

# Function to generate test report
generate_test_report() {
    print_header "Test Report"
    
    echo "Total tests run: $((TESTS_PASSED + TESTS_FAILED))"
    echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
    echo ""
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "${RED}  - $test${NC}"
        done
        echo ""
        echo -e "${YELLOW}Recommendations:${NC}"
        echo "1. Check AWS permissions and credentials"
        echo "2. Verify infrastructure deployment completed successfully"
        echo "3. Check security group rules and network connectivity"
        echo "4. Review CloudWatch logs for application errors"
        echo "5. Verify all GitHub repository secrets are configured"
        echo ""
        return 1
    else
        echo -e "${GREEN}🎉 All tests passed! Your CI/CD pipeline is ready.${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Push changes to dev branch to trigger CI pipeline"
        echo "2. Monitor GitHub Actions for pipeline execution"
        echo "3. Test staging deployment workflow"
        echo "4. Set up production environment when ready"
        return 0
    fi
}

# Main function
main() {
    echo "🧪 FluxTrader CI/CD Pipeline Test Suite"
    echo "This script will test all components of the CI/CD pipeline"
    echo ""
    
    # Run all tests
    test_aws_connectivity
    test_infrastructure_deployment
    test_ec2_instance
    test_rds_database
    test_secrets_manager
    test_local_application
    test_github_workflows
    test_docker_build
    
    # Generate report
    generate_test_report
}

# Run main function
main "$@"

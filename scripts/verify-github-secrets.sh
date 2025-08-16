#!/bin/bash
# Verify and Configure GitHub Repository Secrets
# This script helps verify that all required secrets are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if AWS CLI is configured
check_aws_cli() {
    print_header "Checking AWS CLI Configuration"
    
    if command -v aws &> /dev/null; then
        print_success "AWS CLI is installed"
        
        if aws sts get-caller-identity &> /dev/null; then
            local account_id=$(aws sts get-caller-identity --query Account --output text)
            local user_arn=$(aws sts get-caller-identity --query Arn --output text)
            print_success "AWS CLI is configured and working"
            print_info "Account ID: $account_id"
            print_info "User/Role: $user_arn"
            
            # Check if this is the ankita user
            if echo "$user_arn" | grep -q "ankita"; then
                print_success "Confirmed: Using ankita IAM user"
            else
                print_warning "Current user is not 'ankita': $user_arn"
            fi
            
            return 0
        else
            print_error "AWS CLI is not configured or credentials are invalid"
            return 1
        fi
    else
        print_error "AWS CLI is not installed"
        return 1
    fi
}

# Function to get AWS credentials for GitHub
get_aws_credentials() {
    print_header "Getting AWS Credentials for GitHub Secrets"
    
    if check_aws_cli; then
        echo ""
        print_info "Your current AWS configuration should be added to GitHub secrets:"
        echo ""
        
        # Try to get the access key from AWS CLI config
        local aws_access_key_id=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
        local aws_region=$(aws configure get region 2>/dev/null || echo "us-east-1")
        
        if [[ -n "$aws_access_key_id" ]]; then
            echo "AWS_ACCESS_KEY_ID=$aws_access_key_id"
            echo "AWS_SECRET_ACCESS_KEY=<YOUR_SECRET_ACCESS_KEY_FROM_AWS_CONFIGURE>"
            echo "AWS_KEY_PAIR_NAME=fluxtrader-key"
        else
            print_warning "Could not retrieve access key from AWS CLI config"
            print_info "You may be using temporary credentials or a different auth method"
        fi
        
        echo ""
        print_warning "IMPORTANT: You need to manually get your AWS_SECRET_ACCESS_KEY"
        print_info "If you don't have it, you may need to create a new access key:"
        echo ""
        echo "# Create new access key for ankita user"
        echo "aws iam create-access-key --user-name ankita"
        echo ""
    else
        print_error "Cannot get AWS credentials - AWS CLI not configured"
        return 1
    fi
}

# Function to display required GitHub secrets
display_required_secrets() {
    print_header "Required GitHub Repository Secrets"
    
    echo ""
    print_info "Go to your GitHub repository:"
    echo "https://github.com/Anki246/kamikaze-be/settings/secrets/actions"
    echo ""
    print_info "Add these secrets (click 'New repository secret' for each):"
    echo ""
    
    echo "# ===== CORE AWS CONFIGURATION (CRITICAL) ====="
    echo "AWS_ACCESS_KEY_ID=<YOUR_ANKITA_USER_ACCESS_KEY>"
    echo "AWS_SECRET_ACCESS_KEY=<YOUR_ANKITA_USER_SECRET_KEY>"
    echo "AWS_KEY_PAIR_NAME=fluxtrader-key"
    echo ""
    
    echo "# ===== DATABASE CONFIGURATION ====="
    echo "RDS_MASTER_PASSWORD=admin2025Staging!"
    echo "RDS_MASTER_PASSWORD_PROD=admin2025Prod!"
    echo ""
    
    echo "# ===== STAGING ENVIRONMENT SECRETS ====="
    echo "BINANCE_API_KEY_STAGING=<YOUR_BINANCE_TESTNET_API_KEY>"
    echo "BINANCE_SECRET_KEY_STAGING=<YOUR_BINANCE_TESTNET_SECRET_KEY>"
    echo "JWT_SECRET_STAGING=o0B3UEe8ChHdmTCdFJJsXkYWikZUJG4i"
    echo "ENCRYPTION_KEY_STAGING=NAVtN7ACry1gSgLfpqRsKAZz1Y8HKCNp"
    echo "CREDENTIALS_ENCRYPTION_KEY_STAGING=MMB7CEhv97mhSS9moacXY_8IbN6MIUpHz1ViL_JvL4o="
    echo ""
    
    echo "# ===== PRODUCTION ENVIRONMENT SECRETS ====="
    echo "BINANCE_API_KEY_PROD=<YOUR_BINANCE_PRODUCTION_API_KEY>"
    echo "BINANCE_SECRET_KEY_PROD=<YOUR_BINANCE_PRODUCTION_SECRET_KEY>"
    echo "JWT_SECRET_PROD=DCGx6OykVQFeWz9SrQWGCyeym2Ag0Rws"
    echo "ENCRYPTION_KEY_PROD=SfFIOzFjv7X2ubWu3JA01DqYvd3ZNiYd"
    echo "CREDENTIALS_ENCRYPTION_KEY_PROD=h6ShCwsLRcDFb6jD7TySYQ7aPSbeIzLj"
    echo ""
    
    echo "# ===== ADDITIONAL API KEYS ====="
    echo "GROQ_API_KEY=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"
    echo ""
    
    echo "# ===== OPTIONAL SECRETS ====="
    echo "SONAR_TOKEN=<YOUR_SONARCLOUD_TOKEN>"
    echo "GITLEAKS_LICENSE=<YOUR_GITLEAKS_LICENSE>"
    echo ""
}

# Function to test AWS permissions
test_aws_permissions() {
    print_header "Testing AWS Permissions for CI/CD"
    
    if ! check_aws_cli; then
        return 1
    fi
    
    local tests=(
        "ec2:describe-regions"
        "rds:describe-db-instances --max-items 1"
        "secretsmanager:list-secrets --max-items 1"
        "cloudformation:list-stacks --max-items 1"
        "iam:get-user"
    )
    
    for test in "${tests[@]}"; do
        local service=$(echo "$test" | cut -d: -f1)
        local action=$(echo "$test" | cut -d: -f2-)
        
        if aws $service $action &> /dev/null; then
            print_success "$service permissions working"
        else
            print_error "$service permissions failed"
        fi
    done
}

# Function to create access key for ankita user
create_access_key() {
    print_header "Creating New Access Key for ankita User"
    
    if ! check_aws_cli; then
        print_error "Cannot create access key - AWS CLI not configured"
        return 1
    fi
    
    print_warning "This will create a new access key for the ankita user"
    read -p "Do you want to proceed? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Creating new access key..."
        
        if aws iam create-access-key --user-name ankita; then
            print_success "New access key created successfully!"
            print_warning "IMPORTANT: Save the AccessKeyId and SecretAccessKey from above"
            print_warning "Add these to your GitHub repository secrets immediately"
        else
            print_error "Failed to create access key for ankita user"
            print_info "Make sure the ankita user exists and you have permissions"
        fi
    else
        print_info "Access key creation cancelled"
    fi
}

# Function to fix the current pipeline
fix_current_pipeline() {
    print_header "Fixing Current Pipeline Issue"
    
    echo ""
    print_info "The current pipeline is failing because AWS credentials are not configured in GitHub secrets."
    print_info "Here's how to fix it:"
    echo ""
    
    print_warning "IMMEDIATE ACTION REQUIRED:"
    echo "1. Go to: https://github.com/Anki246/kamikaze-be/settings/secrets/actions"
    echo "2. Add the AWS_ACCESS_KEY_ID secret"
    echo "3. Add the AWS_SECRET_ACCESS_KEY secret"
    echo "4. Re-run the failed workflow"
    echo ""
    
    print_info "To get your AWS credentials:"
    if check_aws_cli; then
        echo "✅ Your AWS CLI is configured - you can use these credentials"
        get_aws_credentials
    else
        echo "❌ Configure AWS CLI first, then run this script again"
    fi
}

# Main function
main() {
    echo "🔍 GitHub Secrets Verification for FluxTrader CI/CD"
    echo "This script helps verify and configure GitHub repository secrets"
    echo ""
    
    # Check current status
    check_aws_cli
    test_aws_permissions
    
    echo ""
    print_info "Choose an action:"
    echo "1. Display required GitHub secrets configuration"
    echo "2. Get AWS credentials for GitHub secrets"
    echo "3. Create new access key for ankita user"
    echo "4. Fix current pipeline issue"
    echo "5. Exit"
    echo ""
    
    read -p "Enter your choice (1-5): " choice
    
    case $choice in
        1)
            display_required_secrets
            ;;
        2)
            get_aws_credentials
            ;;
        3)
            create_access_key
            ;;
        4)
            fix_current_pipeline
            ;;
        5)
            print_info "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    print_success "Script completed!"
    print_info "After configuring GitHub secrets, re-run the pipeline by pushing a new commit"
}

# Run main function
main "$@"

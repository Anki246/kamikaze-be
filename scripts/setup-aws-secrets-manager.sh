#!/bin/bash
# Setup AWS Secrets Manager for FluxTrader CI/CD Pipeline
# This script creates the required secrets in AWS Secrets Manager

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

# Function to check AWS CLI and credentials
check_aws_setup() {
    print_header "Checking AWS Setup"
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        print_info "Please install AWS CLI first"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured"
        print_info "Please run 'aws configure' to set up your credentials"
        exit 1
    fi
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local user_arn=$(aws sts get-caller-identity --query Arn --output text)
    print_success "AWS CLI configured and working"
    print_info "Account ID: $account_id"
    print_info "User/Role: $user_arn"
}

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    print_info "Processing secret: $secret_name"
    
    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "$secret_name" &> /dev/null; then
        print_warning "Secret exists, updating: $secret_name"
        aws secretsmanager update-secret \
            --secret-id "$secret_name" \
            --secret-string "$secret_value"
        print_success "Updated secret: $secret_name"
    else
        print_info "Creating new secret: $secret_name"
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --description "$description" \
            --secret-string "$secret_value"
        print_success "Created secret: $secret_name"
    fi
}

# Function to setup staging secrets
setup_staging_secrets() {
    print_header "Setting Up Staging Environment Secrets"
    
    # Database credentials for staging
    local db_secret='{
        "host": "localhost",
        "port": "5432",
        "database": "kamikaze_staging",
        "username": "fluxtrader",
        "password": "admin2025Staging!",
        "ssl_mode": "prefer",
        "min_size": "5",
        "max_size": "20",
        "timeout": "60"
    }'
    
    create_or_update_secret \
        "fluxtrader/staging/database/main" \
        "$db_secret" \
        "FluxTrader Staging Database Credentials"
    
    # Trading API keys for staging
    local api_keys_secret='{
        "binance_api_key": "staging_api_key_placeholder",
        "binance_secret_key": "staging_secret_key_placeholder",
        "binance_testnet": true,
        "groq_api_key": "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"
    }'
    
    create_or_update_secret \
        "fluxtrader/staging/trading/api-keys" \
        "$api_keys_secret" \
        "FluxTrader Staging Trading API Keys"
    
    # Application secrets for staging
    local app_secrets='{
        "jwt_secret": "o0B3UEe8ChHdmTCdFJJsXkYWikZUJG4i",
        "encryption_key": "NAVtN7ACry1gSgLfpqRsKAZz1Y8HKCNp",
        "credentials_encryption_key": "MMB7CEhv97mhSS9moacXY_8IbN6MIUpHz1ViL_JvL4o="
    }'
    
    create_or_update_secret \
        "fluxtrader/staging/application/secrets" \
        "$app_secrets" \
        "FluxTrader Staging Application Secrets"
}

# Function to setup production secrets
setup_production_secrets() {
    print_header "Setting Up Production Environment Secrets"
    
    # Database credentials for production
    local db_secret='{
        "host": "localhost",
        "port": "5432",
        "database": "kamikaze_production",
        "username": "fluxtrader",
        "password": "admin2025Prod!",
        "ssl_mode": "require",
        "min_size": "10",
        "max_size": "50",
        "timeout": "60"
    }'
    
    create_or_update_secret \
        "fluxtrader/production/database/main" \
        "$db_secret" \
        "FluxTrader Production Database Credentials"
    
    # Trading API keys for production
    local api_keys_secret='{
        "binance_api_key": "production_api_key_placeholder",
        "binance_secret_key": "production_secret_key_placeholder",
        "binance_testnet": false,
        "groq_api_key": "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"
    }'
    
    create_or_update_secret \
        "fluxtrader/production/trading/api-keys" \
        "$api_keys_secret" \
        "FluxTrader Production Trading API Keys"
    
    # Application secrets for production
    local app_secrets='{
        "jwt_secret": "DCGx6OykVQFeWz9SrQWGCyeym2Ag0Rws",
        "encryption_key": "SfFIOzFjv7X2ubWu3JA01DqYvd3ZNiYd",
        "credentials_encryption_key": "h6ShCwsLRcDFb6jD7TySYQ7aPSbeIzLj"
    }'
    
    create_or_update_secret \
        "fluxtrader/production/application/secrets" \
        "$app_secrets" \
        "FluxTrader Production Application Secrets"
}

# Function to setup CI environment secrets
setup_ci_secrets() {
    print_header "Setting Up CI Environment Secrets"
    
    # CI database credentials (for testing)
    local db_secret='{
        "host": "localhost",
        "port": "5432",
        "database": "test_db",
        "username": "test_user",
        "password": "test_pass",
        "ssl_mode": "disable",
        "min_size": "1",
        "max_size": "5",
        "timeout": "30"
    }'
    
    create_or_update_secret \
        "fluxtrader/ci/database/main" \
        "$db_secret" \
        "FluxTrader CI Database Credentials"
    
    # CI API keys (test keys)
    local api_keys_secret='{
        "binance_api_key": "test_api_key",
        "binance_secret_key": "test_secret_key",
        "binance_testnet": true,
        "groq_api_key": "test_groq_key"
    }'
    
    create_or_update_secret \
        "fluxtrader/ci/trading/api-keys" \
        "$api_keys_secret" \
        "FluxTrader CI Trading API Keys"
    
    # CI application secrets
    local app_secrets='{
        "jwt_secret": "ci_jwt_secret_for_testing_only",
        "encryption_key": "ci_encryption_key_for_testing",
        "credentials_encryption_key": "ci_credentials_key_for_testing"
    }'
    
    create_or_update_secret \
        "fluxtrader/ci/application/secrets" \
        "$app_secrets" \
        "FluxTrader CI Application Secrets"
}

# Function to verify secrets
verify_secrets() {
    print_header "Verifying Created Secrets"
    
    local secrets=(
        "fluxtrader/staging/database/main"
        "fluxtrader/staging/trading/api-keys"
        "fluxtrader/staging/application/secrets"
        "fluxtrader/production/database/main"
        "fluxtrader/production/trading/api-keys"
        "fluxtrader/production/application/secrets"
        "fluxtrader/ci/database/main"
        "fluxtrader/ci/trading/api-keys"
        "fluxtrader/ci/application/secrets"
    )
    
    for secret in "${secrets[@]}"; do
        if aws secretsmanager describe-secret --secret-id "$secret" &> /dev/null; then
            print_success "Verified: $secret"
        else
            print_error "Missing: $secret"
        fi
    done
}

# Function to display GitHub secrets configuration
display_github_secrets_config() {
    print_header "GitHub Repository Secrets Configuration"
    
    echo ""
    print_warning "CRITICAL: You must add these secrets to your GitHub repository:"
    print_info "Go to: https://github.com/Anki246/kamikaze-be/settings/secrets/actions"
    echo ""
    
    # Get current AWS credentials
    local access_key_id=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
    local region=$(aws configure get region 2>/dev/null || echo "us-east-1")
    
    echo "# ===== CORE AWS CONFIGURATION (CRITICAL) ====="
    if [[ -n "$access_key_id" ]]; then
        echo "AWS_ACCESS_KEY_ID=$access_key_id"
    else
        echo "AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY_ID>"
    fi
    echo "AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>"
    echo "AWS_KEY_PAIR_NAME=fluxtrader-key"
    echo ""
    
    echo "# ===== DATABASE CONFIGURATION ====="
    echo "RDS_MASTER_PASSWORD=admin2025Staging!"
    echo "RDS_MASTER_PASSWORD_PROD=admin2025Prod!"
    echo ""
    
    echo "# ===== STAGING ENVIRONMENT SECRETS ====="
    echo "BINANCE_API_KEY_STAGING=staging_api_key_placeholder"
    echo "BINANCE_SECRET_KEY_STAGING=staging_secret_key_placeholder"
    echo "JWT_SECRET_STAGING=o0B3UEe8ChHdmTCdFJJsXkYWikZUJG4i"
    echo "ENCRYPTION_KEY_STAGING=NAVtN7ACry1gSgLfpqRsKAZz1Y8HKCNp"
    echo "CREDENTIALS_ENCRYPTION_KEY_STAGING=MMB7CEhv97mhSS9moacXY_8IbN6MIUpHz1ViL_JvL4o="
    echo ""
    
    echo "# ===== ADDITIONAL API KEYS ====="
    echo "GROQ_API_KEY=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"
    echo ""
    
    print_warning "After adding these secrets to GitHub, the CI pipeline should work correctly!"
}

# Main function
main() {
    echo "🔐 AWS Secrets Manager Setup for FluxTrader CI/CD"
    echo "This script creates all required secrets in AWS Secrets Manager"
    echo ""
    
    check_aws_setup
    
    echo ""
    print_info "This script will create secrets for:"
    echo "1. Staging environment"
    echo "2. Production environment"
    echo "3. CI environment"
    echo ""
    
    read -p "Do you want to proceed? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_staging_secrets
        setup_production_secrets
        setup_ci_secrets
        verify_secrets
        display_github_secrets_config
        
        print_success "🎉 AWS Secrets Manager setup completed!"
        print_warning "NEXT STEP: Add the AWS credentials to your GitHub repository secrets"
        print_info "Then re-run the CI/CD pipeline"
    else
        print_info "Setup cancelled"
        exit 0
    fi
}

# Run main function
main "$@"

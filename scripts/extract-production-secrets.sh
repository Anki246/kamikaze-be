#!/bin/bash
# Extract Production Secrets for FluxTrader CI/CD Pipeline
# This script extracts secrets from .env and generates missing ones for GitHub Actions

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

# Function to generate secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to extract value from .env file
extract_env_value() {
    local key=$1
    local env_file=${2:-.env}
    
    if [[ -f "$env_file" ]]; then
        grep "^${key}=" "$env_file" 2>/dev/null | cut -d'=' -f2- | sed 's/^"//' | sed 's/"$//'
    fi
}

# Function to check if .env file exists
check_env_file() {
    if [[ ! -f ".env" ]]; then
        print_error ".env file not found in current directory"
        print_info "Please run this script from the project root directory"
        exit 1
    fi
    print_success ".env file found"
}

# Function to extract existing secrets from .env
extract_existing_secrets() {
    print_header "Extracting Existing Secrets from .env"
    
    # Database secrets
    DB_PASSWORD=$(extract_env_value "DB_PASSWORD")
    GROQ_API_KEY=$(extract_env_value "GROQ_API_KEY")
    CREDENTIALS_ENCRYPTION_KEY=$(extract_env_value "CREDENTIALS_ENCRYPTION_KEY")
    BINANCE_API_KEY=$(extract_env_value "BINANCE_API_KEY")
    BINANCE_SECRET_KEY=$(extract_env_value "BINANCE_SECRET_KEY")
    JWT_SECRET=$(extract_env_value "JWT_SECRET")
    ENCRYPTION_KEY=$(extract_env_value "ENCRYPTION_KEY")
    
    # Display found secrets
    if [[ -n "$DB_PASSWORD" ]]; then
        print_success "Database password found"
    else
        print_warning "Database password not found in .env"
    fi
    
    if [[ -n "$GROQ_API_KEY" ]]; then
        print_success "Groq API key found"
    else
        print_warning "Groq API key not found in .env"
    fi
    
    if [[ -n "$CREDENTIALS_ENCRYPTION_KEY" ]]; then
        print_success "Credentials encryption key found"
    else
        print_warning "Credentials encryption key not found in .env"
    fi
    
    if [[ -n "$BINANCE_API_KEY" ]]; then
        print_success "Binance API key found"
    else
        print_warning "Binance API key not found in .env"
    fi
}

# Function to generate missing secrets
generate_missing_secrets() {
    print_header "Generating Missing Secrets"
    
    # Generate JWT secrets if not found
    if [[ -z "$JWT_SECRET" ]]; then
        JWT_SECRET_STAGING=$(generate_secret 32)
        JWT_SECRET_PROD=$(generate_secret 32)
        print_info "Generated JWT secrets"
    else
        JWT_SECRET_STAGING="$JWT_SECRET"
        JWT_SECRET_PROD=$(generate_secret 32)
        print_info "Using existing JWT secret for staging, generated new for production"
    fi
    
    # Generate encryption keys if not found
    if [[ -z "$ENCRYPTION_KEY" ]]; then
        ENCRYPTION_KEY_STAGING=$(generate_secret 32)
        ENCRYPTION_KEY_PROD=$(generate_secret 32)
        print_info "Generated encryption keys"
    else
        ENCRYPTION_KEY_STAGING="$ENCRYPTION_KEY"
        ENCRYPTION_KEY_PROD=$(generate_secret 32)
        print_info "Using existing encryption key for staging, generated new for production"
    fi
    
    # Use existing credentials encryption key or generate new ones
    if [[ -n "$CREDENTIALS_ENCRYPTION_KEY" ]]; then
        CREDENTIALS_ENCRYPTION_KEY_STAGING="$CREDENTIALS_ENCRYPTION_KEY"
        CREDENTIALS_ENCRYPTION_KEY_PROD=$(generate_secret 32)
        print_info "Using existing credentials encryption key for staging, generated new for production"
    else
        CREDENTIALS_ENCRYPTION_KEY_STAGING=$(generate_secret 32)
        CREDENTIALS_ENCRYPTION_KEY_PROD=$(generate_secret 32)
        print_info "Generated credentials encryption keys"
    fi
    
    # Generate database passwords
    if [[ -n "$DB_PASSWORD" ]]; then
        RDS_MASTER_PASSWORD="${DB_PASSWORD}Staging!"
        RDS_MASTER_PASSWORD_PROD="${DB_PASSWORD}Prod!"
        print_info "Generated RDS passwords based on existing DB password"
    else
        RDS_MASTER_PASSWORD="$(generate_secret 16)Staging!"
        RDS_MASTER_PASSWORD_PROD="$(generate_secret 16)Prod!"
        print_info "Generated new RDS passwords"
    fi
}

# Function to display GitHub secrets configuration
display_github_secrets() {
    print_header "GitHub Repository Secrets Configuration"
    
    echo ""
    echo "🔗 Go to your GitHub repository:"
    echo "   Settings → Secrets and variables → Actions → New repository secret"
    echo ""
    echo "📋 Copy and paste these secrets (one by one):"
    echo ""
    
    # Core AWS Configuration
    echo "# ===== CORE AWS CONFIGURATION (REQUIRED) ====="
    echo "AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY_ID>"
    echo "AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>"
    echo "AWS_KEY_PAIR_NAME=fluxtrader-key"
    echo ""
    
    # Database Configuration
    echo "# ===== DATABASE CONFIGURATION (REQUIRED) ====="
    echo "RDS_MASTER_PASSWORD=$RDS_MASTER_PASSWORD"
    echo "RDS_MASTER_PASSWORD_PROD=$RDS_MASTER_PASSWORD_PROD"
    echo ""
    
    # Staging Environment Secrets
    echo "# ===== STAGING ENVIRONMENT SECRETS (REQUIRED) ====="
    if [[ -n "$BINANCE_API_KEY" ]]; then
        echo "BINANCE_API_KEY_STAGING=$BINANCE_API_KEY"
    else
        echo "BINANCE_API_KEY_STAGING=<YOUR_BINANCE_TESTNET_API_KEY>"
    fi
    
    if [[ -n "$BINANCE_SECRET_KEY" ]]; then
        echo "BINANCE_SECRET_KEY_STAGING=$BINANCE_SECRET_KEY"
    else
        echo "BINANCE_SECRET_KEY_STAGING=<YOUR_BINANCE_TESTNET_SECRET_KEY>"
    fi
    
    echo "JWT_SECRET_STAGING=$JWT_SECRET_STAGING"
    echo "ENCRYPTION_KEY_STAGING=$ENCRYPTION_KEY_STAGING"
    echo "CREDENTIALS_ENCRYPTION_KEY_STAGING=$CREDENTIALS_ENCRYPTION_KEY_STAGING"
    echo ""
    
    # Production Environment Secrets
    echo "# ===== PRODUCTION ENVIRONMENT SECRETS (REQUIRED) ====="
    echo "BINANCE_API_KEY_PROD=<YOUR_BINANCE_PRODUCTION_API_KEY>"
    echo "BINANCE_SECRET_KEY_PROD=<YOUR_BINANCE_PRODUCTION_SECRET_KEY>"
    echo "JWT_SECRET_PROD=$JWT_SECRET_PROD"
    echo "ENCRYPTION_KEY_PROD=$ENCRYPTION_KEY_PROD"
    echo "CREDENTIALS_ENCRYPTION_KEY_PROD=$CREDENTIALS_ENCRYPTION_KEY_PROD"
    echo ""
    
    # Additional API Keys
    echo "# ===== ADDITIONAL API KEYS (REQUIRED) ====="
    if [[ -n "$GROQ_API_KEY" ]]; then
        echo "GROQ_API_KEY=$GROQ_API_KEY"
    else
        echo "GROQ_API_KEY=<YOUR_GROQ_API_KEY>"
    fi
    echo ""
    
    # Optional secrets
    echo "# ===== OPTIONAL SECRETS ====="
    echo "SONAR_TOKEN=<YOUR_SONARCLOUD_TOKEN>  # Optional for code quality"
    echo "GITLEAKS_LICENSE=<YOUR_GITLEAKS_LICENSE>  # Optional for advanced secrets scanning"
    echo ""
}

# Function to highlight missing parameters
highlight_missing_parameters() {
    print_header "Missing Parameters Analysis"
    
    local missing_count=0
    local missing_params=()
    
    # Check AWS credentials
    if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
        missing_params+=("AWS_ACCESS_KEY_ID")
        ((missing_count++))
    fi
    
    if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
        missing_params+=("AWS_SECRET_ACCESS_KEY")
        ((missing_count++))
    fi
    
    # Check Binance API keys
    if [[ -z "$BINANCE_API_KEY" ]]; then
        missing_params+=("BINANCE_API_KEY (for staging)")
        ((missing_count++))
    fi
    
    if [[ -z "$BINANCE_SECRET_KEY" ]]; then
        missing_params+=("BINANCE_SECRET_KEY (for staging)")
        ((missing_count++))
    fi
    
    # Check Groq API key
    if [[ -z "$GROQ_API_KEY" ]]; then
        missing_params+=("GROQ_API_KEY")
        ((missing_count++))
    fi
    
    # Display results
    if [[ $missing_count -eq 0 ]]; then
        print_success "All critical parameters are available!"
    else
        print_warning "Found $missing_count missing critical parameters:"
        for param in "${missing_params[@]}"; do
            print_error "Missing: $param"
        done
        echo ""
        print_info "You need to obtain these values and add them to GitHub secrets"
    fi
    
    # Always missing (need to be obtained)
    print_warning "Parameters that always need to be obtained:"
    print_error "Missing: AWS_ACCESS_KEY_ID (create IAM user)"
    print_error "Missing: AWS_SECRET_ACCESS_KEY (create IAM user)"
    print_error "Missing: BINANCE_API_KEY_PROD (production Binance account)"
    print_error "Missing: BINANCE_SECRET_KEY_PROD (production Binance account)"
}

# Function to create AWS setup commands
create_aws_setup_commands() {
    print_header "AWS Setup Commands"
    
    echo "# 1. Create IAM user for CI/CD"
    echo "aws iam create-user --user-name fluxtrader-cicd"
    echo ""
    echo "# 2. Create access key (save the output!)"
    echo "aws iam create-access-key --user-name fluxtrader-cicd"
    echo ""
    echo "# 3. Create IAM policy file"
    echo "cat > iam-policy.json << 'EOF'"
    echo '{'
    echo '    "Version": "2012-10-17",'
    echo '    "Statement": ['
    echo '        {'
    echo '            "Effect": "Allow",'
    echo '            "Action": ["ec2:*", "rds:*", "secretsmanager:*", "iam:*", "cloudformation:*", "elasticloadbalancing:*", "logs:*", "ssm:*", "sts:GetCallerIdentity"],'
    echo '            "Resource": "*"'
    echo '        }'
    echo '    ]'
    echo '}'
    echo 'EOF'
    echo ""
    echo "# 4. Attach policy to user"
    echo "aws iam put-user-policy --user-name fluxtrader-cicd --policy-name FluxTraderCICDPolicy --policy-document file://iam-policy.json"
    echo ""
    echo "# 5. Create EC2 key pair"
    echo "aws ec2 create-key-pair --key-name fluxtrader-key --query 'KeyMaterial' --output text > fluxtrader-key.pem"
    echo "chmod 400 fluxtrader-key.pem"
}

# Function to create trigger commands
create_trigger_commands() {
    print_header "CI/CD Pipeline Trigger Commands"
    
    echo "# After setting up GitHub secrets, trigger the pipeline:"
    echo ""
    echo "# 1. Switch to dev branch"
    echo "git checkout dev"
    echo ""
    echo "# 2. Make a small change to trigger CI"
    echo "echo \"# CI/CD Test - \$(date)\" >> CICD_TEST_TRIGGER.md"
    echo "git add CICD_TEST_TRIGGER.md"
    echo "git commit -m \"test: trigger CI/CD pipeline\""
    echo ""
    echo "# 3. Push to trigger the pipeline"
    echo "git push origin dev"
    echo ""
    echo "# 4. Monitor the pipeline"
    echo "echo \"Go to GitHub → Actions tab to monitor the pipeline\""
    echo "echo \"Expected workflows: Enhanced CI Pipeline, Deploy to AWS Staging\""
}

# Main function
main() {
    echo "🔐 FluxTrader Production Secrets Extraction"
    echo "This script extracts secrets from .env and prepares GitHub Actions configuration"
    echo ""
    
    check_env_file
    extract_existing_secrets
    generate_missing_secrets
    display_github_secrets
    highlight_missing_parameters
    create_aws_setup_commands
    create_trigger_commands
    
    print_success "Secrets extraction completed!"
    print_warning "Next steps:"
    print_warning "1. Set up AWS IAM user and get access keys"
    print_warning "2. Get Binance API keys (testnet for staging, production for prod)"
    print_warning "3. Add all secrets to GitHub repository"
    print_warning "4. Deploy AWS infrastructure"
    print_warning "5. Trigger CI/CD pipeline"
}

# Run main function
main "$@"

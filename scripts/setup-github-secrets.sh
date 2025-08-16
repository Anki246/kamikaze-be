#!/bin/bash
# GitHub Secrets Setup Script for FluxTrader CI/CD Pipeline
# This script helps generate and display the required GitHub repository secrets

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

# Function to check if required tools are installed
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing_tools=()
    
    if ! command -v openssl &> /dev/null; then
        missing_tools+=("openssl")
    fi
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and run this script again."
        exit 1
    fi
    
    print_success "All required tools are installed"
}

# Function to test AWS connectivity
test_aws_connectivity() {
    print_header "Testing AWS Connectivity"
    
    if aws sts get-caller-identity &> /dev/null; then
        local account_id=$(aws sts get-caller-identity --query Account --output text)
        local user_arn=$(aws sts get-caller-identity --query Arn --output text)
        print_success "AWS connectivity verified"
        print_info "Account ID: $account_id"
        print_info "User/Role: $user_arn"
    else
        print_error "AWS connectivity failed"
        print_warning "Please run 'aws configure' to set up your credentials"
        exit 1
    fi
}

# Function to create EC2 key pair
create_ec2_keypair() {
    print_header "Creating EC2 Key Pair"
    
    local key_name="fluxtrader-dev-key"
    local key_file="${key_name}.pem"
    
    if [ -f "$key_file" ]; then
        print_warning "Key file $key_file already exists"
        read -p "Do you want to create a new key pair? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Using existing key pair: $key_name"
            echo "AWS_KEY_PAIR_NAME=$key_name"
            return
        fi
        rm -f "$key_file"
    fi
    
    if aws ec2 describe-key-pairs --key-names "$key_name" &> /dev/null; then
        print_warning "Key pair $key_name already exists in AWS"
        read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            aws ec2 delete-key-pair --key-name "$key_name"
            print_info "Deleted existing key pair"
        else
            print_info "Using existing key pair: $key_name"
            echo "AWS_KEY_PAIR_NAME=$key_name"
            return
        fi
    fi
    
    print_info "Creating new EC2 key pair: $key_name"
    aws ec2 create-key-pair \
        --key-name "$key_name" \
        --query 'KeyMaterial' \
        --output text > "$key_file"
    
    chmod 400 "$key_file"
    print_success "EC2 key pair created: $key_name"
    print_info "Private key saved to: $key_file"
    print_warning "Keep this file secure and don't commit it to git!"
    
    echo "AWS_KEY_PAIR_NAME=$key_name"
}

# Function to generate all required secrets
generate_secrets() {
    print_header "Generating GitHub Repository Secrets"
    
    echo ""
    echo "Copy and paste these secrets into your GitHub repository:"
    echo "Go to: Repository → Settings → Secrets and variables → Actions"
    echo ""
    
    # AWS Configuration
    echo "# ===== AWS CONFIGURATION ====="
    echo "AWS_ACCESS_KEY_ID=<your-aws-access-key-id>"
    echo "AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>"
    create_ec2_keypair
    echo ""
    
    # Database Passwords
    echo "# ===== DATABASE PASSWORDS ====="
    local staging_db_password=$(generate_secret 16)
    local prod_db_password=$(generate_secret 16)
    echo "RDS_MASTER_PASSWORD=${staging_db_password}Aa1!"
    echo "RDS_MASTER_PASSWORD_PROD=${prod_db_password}Aa1!"
    echo ""
    
    # Staging Environment Secrets
    echo "# ===== STAGING ENVIRONMENT SECRETS ====="
    echo "BINANCE_API_KEY_STAGING=<your-binance-testnet-api-key>"
    echo "BINANCE_SECRET_KEY_STAGING=<your-binance-testnet-secret-key>"
    echo "JWT_SECRET_STAGING=$(generate_secret 32)"
    echo "ENCRYPTION_KEY_STAGING=$(generate_secret 32)"
    echo "CREDENTIALS_ENCRYPTION_KEY_STAGING=$(generate_secret 32)"
    echo ""
    
    # Production Environment Secrets
    echo "# ===== PRODUCTION ENVIRONMENT SECRETS ====="
    echo "BINANCE_API_KEY_PROD=<your-binance-production-api-key>"
    echo "BINANCE_SECRET_KEY_PROD=<your-binance-production-secret-key>"
    echo "JWT_SECRET_PROD=$(generate_secret 32)"
    echo "ENCRYPTION_KEY_PROD=$(generate_secret 32)"
    echo "CREDENTIALS_ENCRYPTION_KEY_PROD=$(generate_secret 32)"
    echo ""
    
    # Additional API Keys
    echo "# ===== ADDITIONAL API KEYS ====="
    echo "GROQ_API_KEY=<your-groq-api-key>"
    echo "SONAR_TOKEN=<your-sonarcloud-token>  # Optional"
    echo "GITLEAKS_LICENSE=<your-gitleaks-license>  # Optional"
    echo ""
}

# Function to create IAM policy file
create_iam_policy() {
    print_header "Creating IAM Policy File"
    
    cat > iam-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "rds:*",
                "secretsmanager:*",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:CreateInstanceProfile",
                "iam:DeleteInstanceProfile",
                "iam:AddRoleToInstanceProfile",
                "iam:RemoveRoleFromInstanceProfile",
                "iam:PassRole",
                "iam:GetRole",
                "iam:GetInstanceProfile",
                "iam:ListInstanceProfilesForRole",
                "iam:CreatePolicy",
                "iam:DeletePolicy",
                "iam:GetPolicy",
                "iam:ListPolicyVersions",
                "cloudformation:*",
                "elasticloadbalancing:*",
                "logs:*",
                "ssm:*",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
EOF
    
    print_success "IAM policy file created: iam-policy.json"
}

# Function to create IAM user and policy
create_iam_user() {
    print_header "Creating IAM User for CI/CD"
    
    local username="fluxtrader-cicd"
    
    # Check if user already exists
    if aws iam get-user --user-name "$username" &> /dev/null; then
        print_warning "IAM user $username already exists"
        read -p "Do you want to recreate the access key? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # List and delete existing access keys
            local access_keys=$(aws iam list-access-keys --user-name "$username" --query 'AccessKeyMetadata[].AccessKeyId' --output text)
            for key in $access_keys; do
                aws iam delete-access-key --user-name "$username" --access-key-id "$key"
                print_info "Deleted existing access key: $key"
            done
        else
            print_info "Skipping IAM user creation"
            return
        fi
    else
        # Create IAM user
        print_info "Creating IAM user: $username"
        aws iam create-user --user-name "$username"
        print_success "IAM user created: $username"
        
        # Attach policy
        print_info "Attaching policy to user"
        aws iam put-user-policy \
            --user-name "$username" \
            --policy-name "FluxTraderCICDPolicy" \
            --policy-document file://iam-policy.json
        print_success "Policy attached to user"
    fi
    
    # Create access key
    print_info "Creating access key for user"
    local access_key_output=$(aws iam create-access-key --user-name "$username")
    local access_key_id=$(echo "$access_key_output" | jq -r '.AccessKey.AccessKeyId')
    local secret_access_key=$(echo "$access_key_output" | jq -r '.AccessKey.SecretAccessKey')
    
    print_success "Access key created successfully"
    echo ""
    print_warning "IMPORTANT: Save these credentials securely!"
    echo "AWS_ACCESS_KEY_ID=$access_key_id"
    echo "AWS_SECRET_ACCESS_KEY=$secret_access_key"
    echo ""
    print_warning "These credentials will not be shown again!"
}

# Function to test IAM permissions
test_iam_permissions() {
    print_header "Testing IAM Permissions"
    
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

# Function to display setup instructions
display_setup_instructions() {
    print_header "Setup Instructions"
    
    echo "1. Copy the generated secrets to your GitHub repository:"
    echo "   - Go to your repository on GitHub"
    echo "   - Navigate to Settings → Secrets and variables → Actions"
    echo "   - Add each secret with the exact name and value shown above"
    echo ""
    echo "2. Create GitHub environment protection rules:"
    echo "   - Go to Settings → Environments"
    echo "   - Create environment: 'staging' (no protection rules)"
    echo "   - Create environment: 'production-approval' (add required reviewers)"
    echo "   - Create environment: 'production' (add required reviewers)"
    echo ""
    echo "3. Test the CI/CD pipeline:"
    echo "   - Make a small change to trigger the pipeline"
    echo "   - Push to the dev branch"
    echo "   - Monitor the GitHub Actions workflow"
    echo ""
    echo "4. Deploy infrastructure:"
    echo "   - Run: ./scripts/deploy-infrastructure.sh --environment staging --tool cloudformation --key-pair fluxtrader-dev-key --password <your-db-password>"
    echo ""
    echo "5. Verify deployment:"
    echo "   - Check CloudFormation stack in AWS console"
    echo "   - Test application health endpoint"
    echo "   - Verify secrets in AWS Secrets Manager"
}

# Main function
main() {
    echo "🚀 FluxTrader CI/CD Pipeline Setup"
    echo "This script will help you set up all required components for testing the CI/CD pipeline"
    echo ""
    
    check_prerequisites
    test_aws_connectivity
    create_iam_policy
    
    read -p "Do you want to create an IAM user for CI/CD? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! command -v jq &> /dev/null; then
            print_error "jq is required for IAM user creation. Please install jq first."
            exit 1
        fi
        create_iam_user
    fi
    
    generate_secrets
    test_iam_permissions
    display_setup_instructions
    
    print_success "Setup script completed!"
    print_warning "Remember to:"
    print_warning "1. Save the generated secrets securely"
    print_warning "2. Add them to your GitHub repository"
    print_warning "3. Keep your EC2 private key file secure"
    print_warning "4. Test the pipeline in a dev environment first"
}

# Run main function
main "$@"

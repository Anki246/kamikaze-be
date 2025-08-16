#!/bin/bash
# FluxTrader Infrastructure Deployment Script
# This script helps deploy AWS infrastructure using either CloudFormation or Terraform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to deploy using CloudFormation
deploy_cloudformation() {
    local environment=$1
    local key_pair_name=$2
    local db_password=$3
    
    print_status "Deploying infrastructure using CloudFormation..."
    
    local stack_name="fluxtrader-${environment}"
    local template_file="infrastructure/cloudformation/fluxtrader-infrastructure.yaml"
    
    if [ ! -f "$template_file" ]; then
        print_error "CloudFormation template not found: $template_file"
        exit 1
    fi
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$stack_name" &> /dev/null; then
        print_status "Stack exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters \
                ParameterKey=Environment,ParameterValue="$environment" \
                ParameterKey=KeyPairName,ParameterValue="$key_pair_name" \
                ParameterKey=DBMasterPassword,ParameterValue="$db_password" \
            --capabilities CAPABILITY_IAM
        
        print_status "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete --stack-name "$stack_name"
    else
        print_status "Creating new stack..."
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters \
                ParameterKey=Environment,ParameterValue="$environment" \
                ParameterKey=KeyPairName,ParameterValue="$key_pair_name" \
                ParameterKey=DBMasterPassword,ParameterValue="$db_password" \
            --capabilities CAPABILITY_IAM
        
        print_status "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name "$stack_name"
    fi
    
    # Get stack outputs
    print_status "Retrieving stack outputs..."
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs' \
        --output table
    
    print_success "CloudFormation deployment completed successfully!"
}

# Function to deploy using Terraform
deploy_terraform() {
    local environment=$1
    
    print_status "Deploying infrastructure using Terraform..."
    
    local terraform_dir="infrastructure/terraform"
    
    if [ ! -d "$terraform_dir" ]; then
        print_error "Terraform directory not found: $terraform_dir"
        exit 1
    fi
    
    cd "$terraform_dir"
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        print_warning "terraform.tfvars not found. Please create it from terraform.tfvars.example"
        print_status "Copying example file..."
        cp terraform.tfvars.example terraform.tfvars
        print_warning "Please edit terraform.tfvars with your configuration before proceeding."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Validate configuration
    print_status "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var="environment=$environment"
    
    # Ask for confirmation
    read -p "Do you want to apply these changes? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled by user"
        exit 0
    fi
    
    # Apply configuration
    print_status "Applying Terraform configuration..."
    terraform apply -var="environment=$environment" -auto-approve
    
    # Show outputs
    print_status "Terraform outputs:"
    terraform output
    
    cd - > /dev/null
    print_success "Terraform deployment completed successfully!"
}

# Function to setup AWS Secrets Manager
setup_secrets_manager() {
    local environment=$1
    
    print_status "Setting up AWS Secrets Manager secrets for $environment environment..."
    
    # Database secrets
    local db_secret_name="fluxtrader/${environment}/database/main"
    print_status "Creating database secrets..."
    
    if aws secretsmanager describe-secret --secret-id "$db_secret_name" &> /dev/null; then
        print_warning "Database secret already exists: $db_secret_name"
    else
        aws secretsmanager create-secret \
            --name "$db_secret_name" \
            --description "FluxTrader $environment Database Credentials" \
            --secret-string '{
                "host": "localhost",
                "port": "5432",
                "database": "kamikaze",
                "username": "fluxtrader",
                "password": "CHANGE_ME",
                "ssl_mode": "prefer",
                "min_size": "5",
                "max_size": "20",
                "timeout": "60"
            }'
        print_success "Database secret created: $db_secret_name"
    fi
    
    # Trading API secrets
    local api_secret_name="fluxtrader/${environment}/trading/api-keys"
    print_status "Creating trading API secrets..."
    
    if aws secretsmanager describe-secret --secret-id "$api_secret_name" &> /dev/null; then
        print_warning "Trading API secret already exists: $api_secret_name"
    else
        aws secretsmanager create-secret \
            --name "$api_secret_name" \
            --description "FluxTrader $environment Trading API Keys" \
            --secret-string '{
                "binance_api_key": "CHANGE_ME",
                "binance_secret_key": "CHANGE_ME",
                "binance_testnet": true,
                "groq_api_key": "CHANGE_ME"
            }'
        print_success "Trading API secret created: $api_secret_name"
    fi
    
    # Application secrets
    local app_secret_name="fluxtrader/${environment}/application/secrets"
    print_status "Creating application secrets..."
    
    if aws secretsmanager describe-secret --secret-id "$app_secret_name" &> /dev/null; then
        print_warning "Application secret already exists: $app_secret_name"
    else
        aws secretsmanager create-secret \
            --name "$app_secret_name" \
            --description "FluxTrader $environment Application Secrets" \
            --secret-string '{
                "jwt_secret": "CHANGE_ME",
                "encryption_key": "CHANGE_ME",
                "credentials_encryption_key": "CHANGE_ME"
            }'
        print_success "Application secret created: $app_secret_name"
    fi
    
    print_warning "Please update the secret values in AWS Secrets Manager console or using AWS CLI"
    print_status "You can update secrets using: aws secretsmanager update-secret --secret-id <secret-name> --secret-string '<json>'"
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV     Environment (staging or production)"
    echo "  -t, --tool TOOL          Deployment tool (cloudformation or terraform)"
    echo "  -k, --key-pair NAME      EC2 Key Pair name (for CloudFormation)"
    echo "  -p, --password PASS      Database master password (for CloudFormation)"
    echo "  -s, --secrets-only       Only setup AWS Secrets Manager"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e staging -t terraform"
    echo "  $0 -e production -t cloudformation -k my-key-pair -p mypassword"
    echo "  $0 -e staging -s"
}

# Main function
main() {
    local environment=""
    local tool=""
    local key_pair_name=""
    local db_password=""
    local secrets_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                environment="$2"
                shift 2
                ;;
            -t|--tool)
                tool="$2"
                shift 2
                ;;
            -k|--key-pair)
                key_pair_name="$2"
                shift 2
                ;;
            -p|--password)
                db_password="$2"
                shift 2
                ;;
            -s|--secrets-only)
                secrets_only=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Validate environment
    if [[ "$environment" != "staging" && "$environment" != "production" ]]; then
        print_error "Environment must be 'staging' or 'production'"
        usage
        exit 1
    fi
    
    print_status "FluxTrader Infrastructure Deployment"
    print_status "Environment: $environment"
    
    # Check prerequisites
    check_prerequisites
    
    # Setup secrets only if requested
    if [ "$secrets_only" = true ]; then
        setup_secrets_manager "$environment"
        exit 0
    fi
    
    # Validate tool selection
    if [[ "$tool" != "cloudformation" && "$tool" != "terraform" ]]; then
        print_error "Tool must be 'cloudformation' or 'terraform'"
        usage
        exit 1
    fi
    
    print_status "Deployment tool: $tool"
    
    # Deploy infrastructure
    case $tool in
        cloudformation)
            if [[ -z "$key_pair_name" || -z "$db_password" ]]; then
                print_error "CloudFormation deployment requires --key-pair and --password options"
                usage
                exit 1
            fi
            deploy_cloudformation "$environment" "$key_pair_name" "$db_password"
            ;;
        terraform)
            deploy_terraform "$environment"
            ;;
    esac
    
    # Setup secrets after infrastructure deployment
    setup_secrets_manager "$environment"
    
    print_success "Infrastructure deployment completed!"
    print_status "Next steps:"
    print_status "1. Update AWS Secrets Manager with actual values"
    print_status "2. Configure GitHub repository secrets for CI/CD"
    print_status "3. Run the CI/CD pipeline to deploy the application"
}

# Run main function with all arguments
main "$@"

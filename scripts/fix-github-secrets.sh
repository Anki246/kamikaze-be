#!/bin/bash
# Fix GitHub Repository Secrets Configuration
# This script helps diagnose and fix GitHub secrets issues

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

# Function to check current AWS setup
check_current_aws_setup() {
    print_header "Checking Current AWS Setup"
    
    if command -v aws &> /dev/null; then
        print_success "AWS CLI is installed"
        
        if aws sts get-caller-identity &> /dev/null; then
            local account_id=$(aws sts get-caller-identity --query Account --output text)
            local user_arn=$(aws sts get-caller-identity --query Arn --output text)
            print_success "AWS CLI is configured and working"
            print_info "Account ID: $account_id"
            print_info "User/Role: $user_arn"
            
            # Extract access key ID if possible
            local access_key_id=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
            if [[ -n "$access_key_id" ]]; then
                print_success "Access Key ID: $access_key_id"
                echo ""
                print_warning "Use this Access Key ID in GitHub secrets!"
            fi
            
            return 0
        else
            print_error "AWS CLI is not configured properly"
            return 1
        fi
    else
        print_error "AWS CLI is not installed"
        return 1
    fi
}

# Function to display the exact GitHub secrets needed
display_exact_github_secrets() {
    print_header "Exact GitHub Repository Secrets Configuration"
    
    echo ""
    print_warning "PROBLEM IDENTIFIED: GitHub repository secrets are not accessible to the workflow"
    print_info "This could be due to:"
    echo "1. Secrets not added to the repository"
    echo "2. Incorrect secret names (case sensitive)"
    echo "3. Repository permissions issues"
    echo "4. Organization-level secret restrictions"
    echo ""
    
    print_info "Go to this EXACT URL:"
    echo "https://github.com/Anki246/kamikaze-be/settings/secrets/actions"
    echo ""
    
    print_info "Click 'New repository secret' and add these EXACT secrets:"
    echo ""
    
    # Get current AWS credentials if available
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
        local access_key_id=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
        
        echo "Name: AWS_ACCESS_KEY_ID"
        if [[ -n "$access_key_id" ]]; then
            echo "Value: $access_key_id"
        else
            echo "Value: <YOUR_AWS_ACCESS_KEY_ID>"
        fi
        echo ""
        
        echo "Name: AWS_SECRET_ACCESS_KEY"
        echo "Value: <YOUR_AWS_SECRET_ACCESS_KEY>"
        echo ""
    else
        echo "Name: AWS_ACCESS_KEY_ID"
        echo "Value: <YOUR_AWS_ACCESS_KEY_ID>"
        echo ""
        
        echo "Name: AWS_SECRET_ACCESS_KEY"
        echo "Value: <YOUR_AWS_SECRET_ACCESS_KEY>"
        echo ""
    fi
    
    echo "Name: AWS_KEY_PAIR_NAME"
    echo "Value: fluxtrader-key"
    echo ""
    
    echo "Name: RDS_MASTER_PASSWORD"
    echo "Value: admin2025Staging!"
    echo ""
    
    echo "Name: RDS_MASTER_PASSWORD_PROD"
    echo "Value: admin2025Prod!"
    echo ""
    
    echo "Name: GROQ_API_KEY"
    echo "Value: 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"
    echo ""
    
    echo "Name: JWT_SECRET_STAGING"
    echo "Value: o0B3UEe8ChHdmTCdFJJsXkYWikZUJG4i"
    echo ""
    
    echo "Name: ENCRYPTION_KEY_STAGING"
    echo "Value: NAVtN7ACry1gSgLfpqRsKAZz1Y8HKCNp"
    echo ""
    
    echo "Name: CREDENTIALS_ENCRYPTION_KEY_STAGING"
    echo "Value: MMB7CEhv97mhSS9moacXY_8IbN6MIUpHz1ViL_JvL4o="
    echo ""
}

# Function to create a test workflow
create_test_workflow() {
    print_header "Creating Test Workflow to Verify Secrets"
    
    cat > .github/workflows/test-secrets.yml << 'EOF'
name: Test GitHub Secrets

on:
  workflow_dispatch:

jobs:
  test-secrets:
    runs-on: ubuntu-latest
    steps:
    - name: Test AWS Credentials
      run: |
        echo "Testing AWS credentials availability..."
        if [ -n "$AWS_ACCESS_KEY_ID" ]; then
          echo "✅ AWS_ACCESS_KEY_ID is available (length: ${#AWS_ACCESS_KEY_ID})"
        else
          echo "❌ AWS_ACCESS_KEY_ID is NOT available"
        fi
        
        if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
          echo "✅ AWS_SECRET_ACCESS_KEY is available (length: ${#AWS_SECRET_ACCESS_KEY})"
        else
          echo "❌ AWS_SECRET_ACCESS_KEY is NOT available"
        fi
        
        if [ -n "$GROQ_API_KEY" ]; then
          echo "✅ GROQ_API_KEY is available (length: ${#GROQ_API_KEY})"
        else
          echo "❌ GROQ_API_KEY is NOT available"
        fi
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
EOF

    print_success "Created test workflow: .github/workflows/test-secrets.yml"
    print_info "This workflow can be manually triggered to test if secrets are working"
}

# Function to provide step-by-step fix instructions
provide_fix_instructions() {
    print_header "Step-by-Step Fix Instructions"
    
    echo ""
    print_warning "STEP 1: Verify Repository Access"
    echo "1. Go to: https://github.com/Anki246/kamikaze-be"
    echo "2. Make sure you have admin access to the repository"
    echo "3. Check if you can see the 'Settings' tab"
    echo ""
    
    print_warning "STEP 2: Add Secrets to Repository"
    echo "1. Go to: https://github.com/Anki246/kamikaze-be/settings/secrets/actions"
    echo "2. Click 'New repository secret'"
    echo "3. Add each secret with EXACT name and value (case sensitive)"
    echo "4. Make sure there are no extra spaces or characters"
    echo ""
    
    print_warning "STEP 3: Verify Secrets Are Added"
    echo "1. After adding secrets, you should see them listed"
    echo "2. Secret values will be hidden (showing only '***')"
    echo "3. Make sure all required secrets are present"
    echo ""
    
    print_warning "STEP 4: Test Secrets"
    echo "1. Go to: https://github.com/Anki246/kamikaze-be/actions"
    echo "2. Click 'Test GitHub Secrets' workflow"
    echo "3. Click 'Run workflow' to test if secrets are accessible"
    echo ""
    
    print_warning "STEP 5: Re-run Main Pipeline"
    echo "1. After secrets are verified working, re-run the main CI pipeline"
    echo "2. Push a new commit or manually trigger the workflow"
    echo ""
}

# Function to create AWS access key
create_aws_access_key() {
    print_header "Creating New AWS Access Key"
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not installed"
        return 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI not configured"
        return 1
    fi
    
    local current_user=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2)
    
    print_warning "This will create a new access key for user: $current_user"
    read -p "Do you want to proceed? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Creating new access key..."
        
        local result=$(aws iam create-access-key --user-name "$current_user" 2>/dev/null)
        
        if [[ $? -eq 0 ]]; then
            print_success "New access key created!"
            echo ""
            print_warning "SAVE THESE CREDENTIALS IMMEDIATELY:"
            echo "$result" | jq -r '"AWS_ACCESS_KEY_ID=" + .AccessKey.AccessKeyId'
            echo "$result" | jq -r '"AWS_SECRET_ACCESS_KEY=" + .AccessKey.SecretAccessKey'
            echo ""
            print_warning "Add these to your GitHub repository secrets NOW!"
        else
            print_error "Failed to create access key"
            print_info "You may need to create it manually in the AWS console"
        fi
    fi
}

# Main function
main() {
    echo "🔧 GitHub Repository Secrets Fix Tool"
    echo "This script helps diagnose and fix GitHub secrets issues"
    echo ""
    
    check_current_aws_setup
    display_exact_github_secrets
    provide_fix_instructions
    
    echo ""
    print_info "Choose an action:"
    echo "1. Create test workflow to verify secrets"
    echo "2. Create new AWS access key"
    echo "3. Show fix instructions again"
    echo "4. Exit"
    echo ""
    
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            create_test_workflow
            print_info "Test workflow created. Commit and push to use it."
            ;;
        2)
            create_aws_access_key
            ;;
        3)
            provide_fix_instructions
            ;;
        4)
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
    print_warning "Remember to add the AWS credentials to GitHub repository secrets!"
}

# Run main function
main "$@"

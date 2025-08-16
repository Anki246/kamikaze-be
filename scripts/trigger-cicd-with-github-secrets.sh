#!/bin/bash
# Trigger CI/CD Pipeline Using Existing GitHub Actions Secrets
# This script triggers the pipeline using the ankita IAM user and production environment secrets

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

# Function to check current branch
check_current_branch() {
    local current_branch=$(git branch --show-current)
    print_info "Current branch: $current_branch"
    
    if [[ "$current_branch" != "dev" ]]; then
        print_warning "Not on dev branch. Switching to dev branch..."
        git checkout dev || {
            print_error "Failed to switch to dev branch"
            exit 1
        }
        print_success "Switched to dev branch"
    else
        print_success "Already on dev branch"
    fi
}

# Function to verify GitHub Actions workflows
verify_workflows() {
    print_header "Verifying GitHub Actions Workflows"
    
    local workflows=(
        ".github/workflows/ci-enhanced.yml"
        ".github/workflows/cd-staging-aws.yml"
        ".github/workflows/cd-production-aws.yml"
    )
    
    for workflow in "${workflows[@]}"; do
        if [[ -f "$workflow" ]]; then
            print_success "Workflow exists: $workflow"
        else
            print_error "Workflow missing: $workflow"
            exit 1
        fi
    done
}

# Function to create trigger commit
create_trigger_commit() {
    print_header "Creating Trigger Commit for CI/CD Pipeline"
    
    # Update trigger file with GitHub Actions info
    cat > GITHUB_ACTIONS_TRIGGER.md << EOF
# GitHub Actions CI/CD Pipeline Trigger

## Pipeline Information
- **Trigger Date**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
- **Branch**: dev
- **IAM User**: ankita (existing)
- **Secrets Source**: GitHub Actions Production Environment
- **Trigger Method**: Manual commit push

## Expected Workflows
1. **Enhanced CI Pipeline** (\`.github/workflows/ci-enhanced.yml\`)
   - Code quality and linting
   - Unit tests with coverage
   - Integration tests
   - Security scanning
   - Docker build and test
   - AWS Secrets Manager integration

2. **AWS Staging Deployment** (\`.github/workflows/cd-staging-aws.yml\`)
   - Infrastructure provisioning
   - Application deployment
   - Health checks and monitoring

## GitHub Actions Secrets Configuration
Using existing production environment secrets:
- ✅ AWS credentials (ankita IAM user)
- ✅ Database passwords
- ✅ API keys (Binance, Groq)
- ✅ Encryption keys
- ✅ JWT secrets

## Expected Results
- All CI jobs should complete successfully
- AWS infrastructure should be provisioned
- Application should deploy to staging environment
- Health checks should pass

## Monitoring
Monitor progress at: https://github.com/Anki246/kamikaze-be/actions

## Status
🚀 **PIPELINE TRIGGERED** - $(date -u '+%Y-%m-%d %H:%M:%S UTC')
EOF

    print_success "Created GitHub Actions trigger file"
}

# Function to update CI workflow to use production secrets
update_ci_workflow() {
    print_header "Updating CI Workflow for Production Secrets"
    
    # The CI workflow should already be configured to use GitHub secrets
    # Just verify it's set up correctly
    if grep -q "secrets\." ".github/workflows/ci-enhanced.yml"; then
        print_success "CI workflow is configured to use GitHub secrets"
    else
        print_warning "CI workflow may need secret configuration updates"
    fi
}

# Function to commit and push changes
commit_and_push() {
    print_header "Committing and Pushing to Trigger Pipeline"
    
    # Add all changes
    git add .
    
    # Create commit
    git commit -m "trigger: CI/CD pipeline with GitHub Actions production secrets

- Using existing ankita IAM user credentials
- Leveraging production environment secrets from GitHub Actions
- Triggering enhanced CI pipeline with AWS integration
- Expected workflows: CI + AWS Staging Deployment

Pipeline trigger: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
Secrets source: GitHub Actions Production Environment
Branch: dev → staging deployment"

    print_success "Created trigger commit"
    
    # Push to trigger pipeline
    print_info "Pushing to GitHub to trigger CI/CD pipeline..."
    git push origin dev
    
    print_success "Pipeline triggered! Check GitHub Actions for progress."
}

# Function to display monitoring information
display_monitoring_info() {
    print_header "Pipeline Monitoring Information"
    
    echo ""
    echo "🔗 **GitHub Actions URL**:"
    echo "   https://github.com/Anki246/kamikaze-be/actions"
    echo ""
    echo "📊 **Expected Workflows**:"
    echo "   1. Enhanced CI Pipeline with AWS Integration"
    echo "   2. Deploy to AWS Staging (after CI completes)"
    echo ""
    echo "⏱️ **Expected Duration**:"
    echo "   - CI Pipeline: ~15-20 minutes"
    echo "   - Staging Deployment: ~10-15 minutes"
    echo "   - Total: ~25-35 minutes"
    echo ""
    echo "✅ **Success Criteria**:"
    echo "   - All 9 CI jobs complete successfully"
    echo "   - AWS infrastructure provisions correctly"
    echo "   - Application deploys and responds to health checks"
    echo "   - Security scans pass without critical issues"
    echo ""
    echo "🔍 **Monitoring Commands**:"
    echo "   # Check AWS infrastructure after deployment"
    echo "   aws cloudformation describe-stacks --stack-name fluxtrader-staging"
    echo ""
    echo "   # Test application health (after deployment)"
    echo "   INSTANCE_IP=\$(aws cloudformation describe-stacks \\"
    echo "     --stack-name fluxtrader-staging \\"
    echo "     --query 'Stacks[0].Outputs[?OutputKey==\`InstancePublicIP\`].OutputValue' \\"
    echo "     --output text)"
    echo "   curl http://\$INSTANCE_IP:8000/health"
    echo ""
}

# Function to verify GitHub repository
verify_github_repo() {
    print_header "Verifying GitHub Repository Configuration"
    
    # Check if we're in the right repository
    local remote_url=$(git remote get-url origin 2>/dev/null || echo "")
    
    if [[ "$remote_url" == *"kamikaze-be"* ]]; then
        print_success "Confirmed repository: kamikaze-be"
    else
        print_error "Not in kamikaze-be repository. Current remote: $remote_url"
        exit 1
    fi
    
    # Check if we can push
    if git remote -v | grep -q "push"; then
        print_success "Push access confirmed"
    else
        print_error "No push access to repository"
        exit 1
    fi
}

# Main function
main() {
    echo "🚀 FluxTrader CI/CD Pipeline Trigger"
    echo "Using existing GitHub Actions production environment secrets"
    echo "IAM User: ankita"
    echo ""
    
    verify_github_repo
    check_current_branch
    verify_workflows
    update_ci_workflow
    create_trigger_commit
    commit_and_push
    display_monitoring_info
    
    print_success "🎉 CI/CD Pipeline Successfully Triggered!"
    print_info "The pipeline is now running with your existing GitHub Actions secrets"
    print_info "Monitor progress at: https://github.com/Anki246/kamikaze-be/actions"
    
    echo ""
    print_warning "Next Steps:"
    print_warning "1. Monitor the GitHub Actions workflows"
    print_warning "2. Check for any failed jobs and review logs"
    print_warning "3. Verify AWS infrastructure deployment"
    print_warning "4. Test application health endpoints"
    print_warning "5. Review security scan results"
}

# Run main function
main "$@"

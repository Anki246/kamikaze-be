# 🧪 CI/CD Pipeline Testing Guide

This guide provides step-by-step instructions to test the FluxTrader CI/CD pipeline in the dev branch, including all required AWS permissions, GitHub secrets, and integration setup.

## 📋 Prerequisites Checklist

### 1. AWS Account Setup
- [ ] Active AWS account with billing enabled
- [ ] AWS CLI v2 installed and configured
- [ ] IAM user with programmatic access
- [ ] EC2 key pair created for SSH access

### 2. GitHub Repository Setup
- [ ] Repository forked/cloned
- [ ] GitHub Actions enabled
- [ ] Admin access to repository settings

### 3. Local Development Environment
- [ ] Git configured with your credentials
- [ ] Docker installed (for local testing)
- [ ] Python 3.11+ installed

## 🔐 Required AWS IAM Permissions

### IAM Policy for CI/CD User
Create an IAM user with the following policies attached:

```json
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
```

### Step-by-Step IAM Setup
```bash
# 1. Create IAM user
aws iam create-user --user-name fluxtrader-cicd

# 2. Create access key
aws iam create-access-key --user-name fluxtrader-cicd

# 3. Create and attach policy
aws iam put-user-policy \
  --user-name fluxtrader-cicd \
  --policy-name FluxTraderCICDPolicy \
  --policy-document file://iam-policy.json

# 4. Create EC2 key pair
aws ec2 create-key-pair \
  --key-name fluxtrader-dev-key \
  --query 'KeyMaterial' \
  --output text > fluxtrader-dev-key.pem

chmod 400 fluxtrader-dev-key.pem
```

## 🔑 Required GitHub Repository Secrets

Navigate to your repository → Settings → Secrets and variables → Actions

### Core AWS Secrets (Required)
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_KEY_PAIR_NAME=fluxtrader-dev-key
```

### Database Secrets (Required)
```
RDS_MASTER_PASSWORD=SecurePassword123!
RDS_MASTER_PASSWORD_PROD=SecureProductionPassword123!
```

### Development Environment Secrets
```
BINANCE_API_KEY_STAGING=your-testnet-api-key
BINANCE_SECRET_KEY_STAGING=your-testnet-secret-key
JWT_SECRET_STAGING=dev-jwt-secret-key-32-chars-min
ENCRYPTION_KEY_STAGING=dev-encryption-key-32-chars-min
CREDENTIALS_ENCRYPTION_KEY_STAGING=dev-creds-key-32-chars-min
```

### Production Environment Secrets (Optional for dev testing)
```
BINANCE_API_KEY_PROD=your-production-api-key
BINANCE_SECRET_KEY_PROD=your-production-secret-key
JWT_SECRET_PROD=prod-jwt-secret-key-32-chars-min
ENCRYPTION_KEY_PROD=prod-encryption-key-32-chars-min
CREDENTIALS_ENCRYPTION_KEY_PROD=prod-creds-key-32-chars-min
```

### Additional API Keys
```
GROQ_API_KEY=gsk_...
SONAR_TOKEN=your-sonarcloud-token (optional)
GITLEAKS_LICENSE=your-gitleaks-license (optional)
```

## 🏗️ Infrastructure Testing Steps

### Step 1: Test AWS Connectivity
```bash
# Test AWS CLI configuration
aws sts get-caller-identity

# Test EC2 permissions
aws ec2 describe-regions

# Test Secrets Manager permissions
aws secretsmanager list-secrets --max-items 1
```

### Step 2: Deploy Development Infrastructure
```bash
# Clone repository and switch to dev branch
git clone https://github.com/your-username/kamikaze-be.git
cd kamikaze-be
git checkout dev

# Make scripts executable
chmod +x scripts/deploy-infrastructure.sh
chmod +x scripts/user-data-staging.sh
chmod +x scripts/user-data-production.sh

# Deploy development infrastructure
./scripts/deploy-infrastructure.sh \
  --environment staging \
  --tool cloudformation \
  --key-pair fluxtrader-dev-key \
  --password SecurePassword123!
```

### Step 3: Verify Infrastructure Deployment
```bash
# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name fluxtrader-staging

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs' \
  --output table

# Test EC2 instance
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
  --output text)

aws ec2 describe-instances --instance-ids $INSTANCE_ID
```

### Step 4: Verify Secrets Manager Setup
```bash
# List FluxTrader secrets
aws secretsmanager list-secrets \
  --query 'SecretList[?contains(Name, `fluxtrader`)]' \
  --output table

# Test secret retrieval
aws secretsmanager get-secret-value \
  --secret-id fluxtrader/staging/database/main \
  --query 'SecretString' \
  --output text
```

## 🚀 CI/CD Pipeline Testing

### Step 1: Test Enhanced CI Pipeline

#### Trigger CI Pipeline
```bash
# Make a small change to trigger CI
echo "# CI/CD Test - $(date)" >> README.md
git add README.md
git commit -m "test: trigger CI pipeline"
git push origin dev
```

#### Monitor CI Pipeline
1. Go to GitHub repository → Actions tab
2. Look for "Enhanced CI Pipeline with AWS Integration" workflow
3. Monitor the following jobs:
   - [ ] Setup & Cache Management
   - [ ] Code Quality & Linting
   - [ ] AWS Secrets Manager Integration
   - [ ] Unit Tests & Coverage
   - [ ] Integration Tests
   - [ ] Build Verification
   - [ ] Enhanced Security Scan
   - [ ] Docker Build & Test
   - [ ] CI Summary

#### Expected CI Results
- [ ] All jobs complete successfully (green checkmarks)
- [ ] AWS Secrets Manager integration test passes
- [ ] Code coverage meets 70% threshold
- [ ] Security scans complete without critical issues
- [ ] Docker image builds successfully

### Step 2: Test AWS Staging Deployment

#### Trigger Staging Deployment
```bash
# Push to dev branch (if configured) or manually trigger
git push origin dev

# OR manually trigger via GitHub Actions:
# 1. Go to Actions → "Deploy to AWS Staging"
# 2. Click "Run workflow"
# 3. Select "dev" branch
# 4. Click "Run workflow"
```

#### Monitor Staging Deployment
1. Watch the deployment workflow progress
2. Monitor the following jobs:
   - [ ] Pre-deployment Validation
   - [ ] Build & Push to Registry
   - [ ] AWS Infrastructure Setup
   - [ ] Deploy to AWS Staging
   - [ ] Post-deployment Monitoring

#### Verify Staging Deployment
```bash
# Get instance public IP
PUBLIC_IP=$(aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIP`].OutputValue' \
  --output text)

# Test health endpoint
curl -f http://$PUBLIC_IP:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "2024-01-15T10:30:00Z", "version": "dev"}

# Test API documentation
curl -f http://$PUBLIC_IP:8000/docs
```

### Step 3: Test Application Functionality

#### SSH to Instance
```bash
# SSH to the staging instance
ssh -i fluxtrader-dev-key.pem ec2-user@$PUBLIC_IP

# Check container status
docker ps

# Check application logs
docker logs fluxtrader-staging

# Check system logs
tail -f /opt/fluxtrader/logs/system/health-check.log
```

#### Test AWS Secrets Integration
```bash
# On the EC2 instance, test secrets retrieval
python3 -c "
import sys
sys.path.insert(0, '/opt/fluxtrader/src')
import asyncio
from infrastructure.aws_secrets_manager import get_database_credentials

async def test():
    creds = await get_database_credentials()
    print(f'Database host: {creds.host}')
    print('✅ Secrets integration working')

asyncio.run(test())
"
```

## 🔍 Troubleshooting Common Issues

### Issue 1: AWS Permissions Denied
```bash
# Check IAM user permissions
aws iam get-user-policy --user-name fluxtrader-cicd --policy-name FluxTraderCICDPolicy

# Test specific permissions
aws ec2 describe-instances --max-items 1
aws secretsmanager list-secrets --max-items 1
aws cloudformation list-stacks --max-items 1
```

### Issue 2: GitHub Secrets Not Working
```bash
# Verify secrets are set correctly
# Go to GitHub → Settings → Secrets and variables → Actions
# Check all required secrets are present and have correct values
```

### Issue 3: Infrastructure Deployment Fails
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name fluxtrader-staging

# Check specific resource failures
aws cloudformation describe-stack-resources --stack-name fluxtrader-staging
```

### Issue 4: Application Health Check Fails
```bash
# SSH to instance and debug
ssh -i fluxtrader-dev-key.pem ec2-user@$PUBLIC_IP

# Check Docker container
docker ps -a
docker logs fluxtrader-staging

# Check user-data script execution
sudo tail -f /var/log/user-data.log

# Check application startup
sudo journalctl -u fluxtrader.service -f
```

### Issue 5: Secrets Manager Integration Fails
```bash
# Test secrets from EC2 instance
aws secretsmanager get-secret-value --secret-id fluxtrader/staging/database/main

# Check IAM role permissions
aws sts get-caller-identity

# Verify instance profile
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

## ✅ Testing Checklist

### Pre-deployment Checklist
- [ ] AWS CLI configured with correct credentials
- [ ] IAM user has all required permissions
- [ ] EC2 key pair created and accessible
- [ ] GitHub repository secrets configured
- [ ] GitHub Actions enabled

### Infrastructure Testing Checklist
- [ ] CloudFormation stack deploys successfully
- [ ] EC2 instance launches and is accessible
- [ ] RDS instance creates and is accessible
- [ ] Security groups configured correctly
- [ ] IAM roles and instance profiles created
- [ ] Secrets Manager secrets created

### CI Pipeline Testing Checklist
- [ ] Code quality checks pass
- [ ] Unit tests pass with adequate coverage
- [ ] Integration tests complete successfully
- [ ] Security scans complete without critical issues
- [ ] Docker image builds and scans successfully
- [ ] AWS integration tests pass

### CD Pipeline Testing Checklist
- [ ] Staging deployment completes successfully
- [ ] Application starts and responds to health checks
- [ ] Secrets Manager integration works
- [ ] Database connectivity established
- [ ] API endpoints accessible
- [ ] Monitoring and logging configured

### Post-deployment Verification Checklist
- [ ] Application health endpoint returns 200
- [ ] API documentation accessible at /docs
- [ ] CloudWatch logs are being generated
- [ ] Health check cron job is running
- [ ] Backup scripts are configured
- [ ] Security monitoring is active

## 🎯 Success Criteria

The CI/CD pipeline testing is successful when:

1. **✅ CI Pipeline**: All jobs complete successfully with green status
2. **✅ Infrastructure**: AWS resources deploy without errors
3. **✅ Application**: Health checks return successful responses
4. **✅ Security**: All security scans pass without critical issues
5. **✅ Integration**: AWS Secrets Manager integration works correctly
6. **✅ Monitoring**: CloudWatch logs and metrics are being collected
7. **✅ Rollback**: Rollback mechanisms function correctly (test by introducing a failure)

## 📞 Support

If you encounter issues during testing:

1. **Check the logs**: GitHub Actions logs, CloudWatch logs, application logs
2. **Verify permissions**: Ensure all AWS IAM permissions are correctly set
3. **Test connectivity**: Verify network connectivity and security group rules
4. **Review configuration**: Double-check all secrets and environment variables
5. **Consult documentation**: Refer to the comprehensive AWS Deployment Guide

Remember to clean up test resources after testing to avoid unnecessary AWS charges:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name fluxtrader-staging

# Delete secrets (optional)
aws secretsmanager delete-secret --secret-id fluxtrader/staging/database/main --force-delete-without-recovery
```

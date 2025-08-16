# 🚀 FluxTrader CI/CD Pipeline - Complete Setup Requirements

## 📋 Quick Setup Checklist

### ✅ Prerequisites
- [ ] AWS Account with billing enabled
- [ ] GitHub repository with admin access
- [ ] AWS CLI v2 installed and configured
- [ ] Git configured with your credentials

### ✅ AWS Setup
- [ ] IAM user created with required permissions
- [ ] EC2 key pair created for SSH access
- [ ] AWS credentials configured locally

### ✅ GitHub Setup
- [ ] Repository secrets configured (see list below)
- [ ] Environment protection rules set up
- [ ] GitHub Actions enabled

### ✅ Infrastructure
- [ ] AWS infrastructure deployed (CloudFormation/Terraform)
- [ ] Secrets Manager configured with application secrets
- [ ] EC2 instance running and accessible

### ✅ Testing
- [ ] CI pipeline triggered and passing
- [ ] Application health checks responding
- [ ] AWS integration working correctly

## 🔐 Required AWS IAM Permissions

### IAM Policy JSON
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
                "iam:CreatePolicy",
                "iam:DeletePolicy",
                "iam:GetPolicy",
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

## 🔑 Required GitHub Repository Secrets

### Core AWS Configuration (REQUIRED)
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_KEY_PAIR_NAME=fluxtrader-dev-key
```

### Database Configuration (REQUIRED)
```
RDS_MASTER_PASSWORD=SecurePassword123!
RDS_MASTER_PASSWORD_PROD=SecureProductionPassword123!
```

### Staging Environment Secrets (REQUIRED)
```
BINANCE_API_KEY_STAGING=your-testnet-api-key
BINANCE_SECRET_KEY_STAGING=your-testnet-secret-key
JWT_SECRET_STAGING=generated-32-char-secret
ENCRYPTION_KEY_STAGING=generated-32-char-key
CREDENTIALS_ENCRYPTION_KEY_STAGING=generated-32-char-key
```

### Production Environment Secrets (OPTIONAL for dev testing)
```
BINANCE_API_KEY_PROD=your-production-api-key
BINANCE_SECRET_KEY_PROD=your-production-secret-key
JWT_SECRET_PROD=generated-32-char-secret
ENCRYPTION_KEY_PROD=generated-32-char-key
CREDENTIALS_ENCRYPTION_KEY_PROD=generated-32-char-key
```

### Additional API Keys (REQUIRED)
```
GROQ_API_KEY=gsk_...
SONAR_TOKEN=your-sonarcloud-token (optional)
GITLEAKS_LICENSE=your-gitleaks-license (optional)
```

## 🚀 Step-by-Step Setup Process

### Step 1: Generate Secrets Automatically
```bash
# Run the automated setup script
chmod +x scripts/setup-github-secrets.sh
./scripts/setup-github-secrets.sh
```

### Step 2: Deploy AWS Infrastructure
```bash
# Deploy staging infrastructure
chmod +x scripts/deploy-infrastructure.sh
./scripts/deploy-infrastructure.sh \
  --environment staging \
  --tool cloudformation \
  --key-pair fluxtrader-dev-key \
  --password SecurePassword123!
```

### Step 3: Configure GitHub Repository
1. Go to your repository → Settings → Secrets and variables → Actions
2. Add all the secrets generated in Step 1
3. Create environments:
   - `staging` (no protection)
   - `production-approval` (required reviewers)
   - `production` (required reviewers)

### Step 4: Test the Pipeline
```bash
# Test the complete pipeline
chmod +x scripts/test-cicd-pipeline.sh
./scripts/test-cicd-pipeline.sh

# Trigger CI pipeline by pushing to dev branch
git checkout dev
echo "# CI Test - $(date)" >> CICD_TEST_TRIGGER.md
git add CICD_TEST_TRIGGER.md
git commit -m "test: trigger CI pipeline"
git push origin dev
```

### Step 5: Monitor and Verify
1. Go to GitHub Actions tab
2. Watch the "Enhanced CI Pipeline" workflow
3. Verify all jobs complete successfully
4. Check application health endpoint

## 🧪 Testing Commands

### Test AWS Connectivity
```bash
aws sts get-caller-identity
aws ec2 describe-regions --max-items 1
aws secretsmanager list-secrets --max-items 1
```

### Test Infrastructure
```bash
# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name fluxtrader-staging

# Get instance IP
INSTANCE_IP=$(aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIP`].OutputValue' \
  --output text)

# Test application health
curl http://$INSTANCE_IP:8000/health
```

### Test Secrets Manager
```bash
# Test secret retrieval
aws secretsmanager get-secret-value \
  --secret-id fluxtrader/staging/database/main \
  --query 'SecretString' \
  --output text
```

## 🔍 Troubleshooting Common Issues

### Issue: AWS Permissions Denied
**Solution**: Verify IAM user has all required permissions
```bash
aws iam get-user-policy --user-name fluxtrader-cicd --policy-name FluxTraderCICDPolicy
```

### Issue: GitHub Actions Failing
**Solution**: Check repository secrets are correctly configured
- Verify all required secrets are present
- Check secret values don't have extra spaces or characters

### Issue: Infrastructure Deployment Fails
**Solution**: Check CloudFormation events
```bash
aws cloudformation describe-stack-events --stack-name fluxtrader-staging
```

### Issue: Application Not Responding
**Solution**: Check EC2 instance and container status
```bash
# SSH to instance
ssh -i fluxtrader-dev-key.pem ec2-user@$INSTANCE_IP

# Check container
docker ps
docker logs fluxtrader-staging

# Check application logs
tail -f /opt/fluxtrader/logs/system/health-check.log
```

## 📊 Expected Results

### Successful CI Pipeline
- ✅ All 9 CI jobs complete with green status
- ✅ Code coverage meets 70% threshold
- ✅ Security scans pass without critical issues
- ✅ Docker image builds successfully
- ✅ AWS integration tests pass

### Successful Infrastructure Deployment
- ✅ CloudFormation stack creates successfully
- ✅ EC2 instance launches and is accessible
- ✅ RDS instance creates and is available
- ✅ Secrets Manager contains all required secrets
- ✅ Security groups configured correctly

### Successful Application Deployment
- ✅ Application container starts successfully
- ✅ Health endpoint returns 200 status
- ✅ API documentation accessible at /docs
- ✅ AWS Secrets Manager integration working
- ✅ Database connectivity established

## 🎯 Success Criteria

The CI/CD pipeline is successfully set up when:

1. **✅ CI Pipeline**: All GitHub Actions workflows complete successfully
2. **✅ Infrastructure**: AWS resources are provisioned and accessible
3. **✅ Application**: Health checks return successful responses
4. **✅ Security**: All security scans pass without critical vulnerabilities
5. **✅ Integration**: AWS Secrets Manager integration works correctly
6. **✅ Monitoring**: CloudWatch logs and metrics are being collected

## 📞 Next Steps After Setup

1. **Production Setup**: Repeat process with production environment
2. **Monitoring**: Set up CloudWatch alarms and notifications
3. **Security**: Review and harden security configurations
4. **Optimization**: Monitor costs and optimize resource usage
5. **Documentation**: Update team documentation with access procedures

## 🔗 Quick Links

- [Complete Testing Guide](docs/CICD_TESTING_GUIDE.md)
- [AWS Deployment Guide](docs/AWS_DEPLOYMENT_GUIDE.md)
- [Quick Start Guide](docs/QUICK_START_AWS.md)
- [Infrastructure Templates](infrastructure/)

---

**🎉 Ready to Test!** 

The dev branch now contains the complete CI/CD pipeline with AWS integration. Follow the steps above to set up and test the pipeline in your environment.

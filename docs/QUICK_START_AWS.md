# ⚡ FluxTrader AWS Quick Start Guide

Get FluxTrader running on AWS in under 30 minutes with this streamlined setup guide.

## 🚀 Prerequisites (5 minutes)

### 1. Install Required Tools
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

### 2. Create EC2 Key Pair
```bash
# Create key pair for SSH access
aws ec2 create-key-pair \
  --key-name fluxtrader-key \
  --query 'KeyMaterial' \
  --output text > fluxtrader-key.pem

chmod 400 fluxtrader-key.pem
```

## 🏗️ Infrastructure Setup (10 minutes)

### Option A: Quick CloudFormation Deployment
```bash
# Clone the repository
git clone https://github.com/your-username/kamikaze-be.git
cd kamikaze-be

# Make deployment script executable
chmod +x scripts/deploy-infrastructure.sh

# Deploy staging environment
./scripts/deploy-infrastructure.sh \
  --environment staging \
  --tool cloudformation \
  --key-pair fluxtrader-key \
  --password MySecurePassword123!

# Wait for completion (5-10 minutes)
```

### Option B: Terraform Deployment
```bash
cd infrastructure/terraform

# Copy and edit configuration
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Update with your values

# Deploy
terraform init
terraform apply -auto-approve
```

## 🔐 Configure Secrets (5 minutes)

### 1. Update Database Credentials
```bash
# Get RDS endpoint from CloudFormation output
RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
  --output text)

# Update database secret
aws secretsmanager update-secret \
  --secret-id "fluxtrader/staging/database/main" \
  --secret-string "{
    \"host\": \"$RDS_ENDPOINT\",
    \"port\": \"5432\",
    \"database\": \"kamikaze\",
    \"username\": \"fluxtrader\",
    \"password\": \"MySecurePassword123!\",
    \"ssl_mode\": \"require\",
    \"min_size\": \"5\",
    \"max_size\": \"20\",
    \"timeout\": \"60\"
  }"
```

### 2. Update Trading API Keys
```bash
# Update with your actual API keys
aws secretsmanager update-secret \
  --secret-id "fluxtrader/staging/trading/api-keys" \
  --secret-string '{
    "binance_api_key": "YOUR_BINANCE_API_KEY",
    "binance_secret_key": "YOUR_BINANCE_SECRET_KEY",
    "binance_testnet": true,
    "groq_api_key": "YOUR_GROQ_API_KEY"
  }'
```

### 3. Update Application Secrets
```bash
# Generate secure secrets
JWT_SECRET=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)
CREDENTIALS_KEY=$(openssl rand -base64 32)

aws secretsmanager update-secret \
  --secret-id "fluxtrader/staging/application/secrets" \
  --secret-string "{
    \"jwt_secret\": \"$JWT_SECRET\",
    \"encryption_key\": \"$ENCRYPTION_KEY\",
    \"credentials_encryption_key\": \"$CREDENTIALS_KEY\"
  }"
```

## 🔧 GitHub Setup (5 minutes)

### 1. Fork Repository
1. Go to https://github.com/your-username/kamikaze-be
2. Click "Fork" to create your copy

### 2. Configure Repository Secrets
Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:
```
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_KEY_PAIR_NAME=fluxtrader-key
RDS_MASTER_PASSWORD=MySecurePassword123!
BINANCE_API_KEY_STAGING=your-staging-binance-api-key
BINANCE_SECRET_KEY_STAGING=your-staging-binance-secret-key
GROQ_API_KEY=your-groq-api-key
JWT_SECRET_STAGING=generated-jwt-secret
ENCRYPTION_KEY_STAGING=generated-encryption-key
CREDENTIALS_ENCRYPTION_KEY_STAGING=generated-credentials-key
```

### 3. Create Environment
1. Go to Settings → Environments
2. Create environment: `staging`
3. No protection rules needed

## 🚀 Deploy Application (5 minutes)

### 1. Trigger Deployment
1. Go to Actions tab in your GitHub repository
2. Select "Deploy to AWS Staging" workflow
3. Click "Run workflow"
4. Use default settings and click "Run workflow"

### 2. Monitor Deployment
- Watch the workflow progress in GitHub Actions
- Deployment takes 5-10 minutes
- Check for green checkmarks on all jobs

### 3. Verify Deployment
```bash
# Get instance IP from CloudFormation
INSTANCE_IP=$(aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`InstancePublicIP`].OutputValue' \
  --output text)

# Test health endpoint
curl http://$INSTANCE_IP:8000/health

# Expected response: {"status": "healthy", "timestamp": "..."}
```

## 🎯 Quick Verification Checklist

- [ ] AWS infrastructure deployed successfully
- [ ] Secrets updated in AWS Secrets Manager
- [ ] GitHub repository secrets configured
- [ ] CI/CD pipeline runs without errors
- [ ] Application responds to health checks
- [ ] Can access application at `http://INSTANCE_IP:8000`

## 🔍 Quick Troubleshooting

### Issue: Health check fails
```bash
# SSH to instance
ssh -i fluxtrader-key.pem ec2-user@$INSTANCE_IP

# Check container status
docker ps

# Check logs
docker logs fluxtrader-staging

# Check application logs
tail -f /opt/fluxtrader/logs/system/health-check.log
```

### Issue: Secrets not loading
```bash
# Verify secrets exist
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `fluxtrader`)]'

# Test secret retrieval
aws secretsmanager get-secret-value --secret-id fluxtrader/staging/database/main
```

### Issue: CI/CD pipeline fails
1. Check GitHub Actions logs for specific error
2. Verify all repository secrets are set correctly
3. Ensure AWS credentials have proper permissions

## 🎉 Next Steps

### Production Deployment
1. Follow the same process with `--environment production`
2. Set up production secrets with real API keys
3. Configure production environment protection in GitHub
4. Use manual deployment workflow for production

### Monitoring Setup
1. Check CloudWatch logs: `/fluxtrader/staging/system`
2. Set up CloudWatch alarms for critical metrics
3. Configure SNS notifications for alerts

### Security Hardening
1. Restrict security group access to your IP
2. Enable AWS CloudTrail for audit logging
3. Set up AWS Config for compliance monitoring
4. Rotate secrets regularly

## 📚 Additional Resources

- [Complete AWS Deployment Guide](AWS_DEPLOYMENT_GUIDE.md)
- [CI/CD Pipeline Documentation](CI_CD_PIPELINE.md)
- [FluxTrader Configuration Guide](../README.md)

---

**🎊 Congratulations!** You now have FluxTrader running on AWS with a complete CI/CD pipeline, secure secret management, and production-ready infrastructure!

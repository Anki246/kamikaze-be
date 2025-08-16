# 🚀 FluxTrader AWS Deployment Guide

This comprehensive guide covers deploying FluxTrader to AWS using the enhanced CI/CD pipeline with AWS Secrets Manager integration.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Infrastructure Setup](#aws-infrastructure-setup)
3. [Secrets Manager Configuration](#secrets-manager-configuration)
4. [GitHub Repository Setup](#github-repository-setup)
5. [CI/CD Pipeline Configuration](#cicd-pipeline-configuration)
6. [Deployment Process](#deployment-process)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Required Tools
- **AWS CLI v2**: [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Terraform** (optional): [Installation Guide](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- **Docker**: [Installation Guide](https://docs.docker.com/get-docker/)
- **Git**: [Installation Guide](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

### AWS Account Setup
1. **AWS Account**: Active AWS account with appropriate permissions
2. **IAM User**: Create an IAM user with the following policies:
   - `AmazonEC2FullAccess`
   - `AmazonRDSFullAccess`
   - `SecretsManagerReadWrite`
   - `CloudFormationFullAccess` (if using CloudFormation)
   - `IAMFullAccess` (for creating roles and policies)

3. **EC2 Key Pair**: Create an EC2 key pair for SSH access
4. **AWS CLI Configuration**: Configure AWS CLI with your credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, region, and output format
```

### GitHub Account Setup
1. **GitHub Repository**: Fork or clone the FluxTrader repository
2. **GitHub Actions**: Ensure GitHub Actions is enabled for your repository

## 🏗️ AWS Infrastructure Setup

FluxTrader provides two options for infrastructure deployment: **CloudFormation** and **Terraform**.

### Option 1: CloudFormation Deployment

#### Quick Start
```bash
# Make the deployment script executable
chmod +x scripts/deploy-infrastructure.sh

# Deploy staging environment
./scripts/deploy-infrastructure.sh \
  --environment staging \
  --tool cloudformation \
  --key-pair your-ec2-key-pair-name \
  --password your-secure-db-password

# Deploy production environment
./scripts/deploy-infrastructure.sh \
  --environment production \
  --tool cloudformation \
  --key-pair your-ec2-key-pair-name \
  --password your-secure-db-password
```

#### Manual CloudFormation Deployment
```bash
# Create staging stack
aws cloudformation create-stack \
  --stack-name fluxtrader-staging \
  --template-body file://infrastructure/cloudformation/fluxtrader-infrastructure.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=staging \
    ParameterKey=KeyPairName,ParameterValue=your-key-pair \
    ParameterKey=DBMasterPassword,ParameterValue=your-password \
  --capabilities CAPABILITY_IAM

# Wait for completion
aws cloudformation wait stack-create-complete --stack-name fluxtrader-staging

# Get outputs
aws cloudformation describe-stacks \
  --stack-name fluxtrader-staging \
  --query 'Stacks[0].Outputs'
```

### Option 2: Terraform Deployment

#### Setup Terraform
```bash
cd infrastructure/terraform

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
nano terraform.tfvars
```

#### Example terraform.tfvars
```hcl
# Environment configuration
environment = "staging"

# AWS configuration
aws_region = "us-east-1"

# EC2 configuration
instance_type = "t3.medium"
key_pair_name = "your-ec2-key-pair-name"

# RDS configuration
rds_instance_class = "db.t3.micro"
db_master_password = "your-secure-database-password"

# Security configuration
allowed_cidr = "0.0.0.0/0"  # Restrict for production
```

#### Deploy with Terraform
```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Get outputs
terraform output
```

#### Quick Terraform Deployment
```bash
# Deploy staging environment
./scripts/deploy-infrastructure.sh \
  --environment staging \
  --tool terraform

# Deploy production environment
./scripts/deploy-infrastructure.sh \
  --environment production \
  --tool terraform
```

## 🔐 Secrets Manager Configuration

### Automatic Setup
The deployment script automatically creates placeholder secrets:

```bash
# Setup secrets for staging
./scripts/deploy-infrastructure.sh --environment staging --secrets-only

# Setup secrets for production
./scripts/deploy-infrastructure.sh --environment production --secrets-only
```

### Manual Secrets Configuration

#### 1. Database Credentials
```bash
aws secretsmanager create-secret \
  --name "fluxtrader/staging/database/main" \
  --description "FluxTrader Staging Database Credentials" \
  --secret-string '{
    "host": "your-rds-endpoint",
    "port": "5432",
    "database": "kamikaze",
    "username": "fluxtrader",
    "password": "your-db-password",
    "ssl_mode": "require",
    "min_size": "5",
    "max_size": "20",
    "timeout": "60"
  }'
```

#### 2. Trading API Keys
```bash
aws secretsmanager create-secret \
  --name "fluxtrader/staging/trading/api-keys" \
  --description "FluxTrader Staging Trading API Keys" \
  --secret-string '{
    "binance_api_key": "your-binance-api-key",
    "binance_secret_key": "your-binance-secret-key",
    "binance_testnet": true,
    "groq_api_key": "your-groq-api-key"
  }'
```

#### 3. Application Secrets
```bash
aws secretsmanager create-secret \
  --name "fluxtrader/staging/application/secrets" \
  --description "FluxTrader Staging Application Secrets" \
  --secret-string '{
    "jwt_secret": "your-jwt-secret-key",
    "encryption_key": "your-encryption-key",
    "credentials_encryption_key": "your-credentials-encryption-key"
  }'
```

### Update Existing Secrets
```bash
# Update database credentials
aws secretsmanager update-secret \
  --secret-id "fluxtrader/staging/database/main" \
  --secret-string '{
    "host": "updated-rds-endpoint",
    "port": "5432",
    "database": "kamikaze",
    "username": "fluxtrader",
    "password": "updated-password",
    "ssl_mode": "require",
    "min_size": "5",
    "max_size": "20",
    "timeout": "60"
  }'
```

## 🔧 GitHub Repository Setup

### 1. Repository Secrets Configuration

Navigate to your GitHub repository → Settings → Secrets and variables → Actions

#### Required Secrets

**AWS Configuration:**
```
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_KEY_PAIR_NAME=your-ec2-key-pair-name
```

**Database Passwords:**
```
RDS_MASTER_PASSWORD=your-staging-db-password
RDS_MASTER_PASSWORD_PROD=your-production-db-password
```

**Staging Environment Secrets:**
```
BINANCE_API_KEY_STAGING=your-staging-binance-api-key
BINANCE_SECRET_KEY_STAGING=your-staging-binance-secret-key
JWT_SECRET_STAGING=your-staging-jwt-secret
ENCRYPTION_KEY_STAGING=your-staging-encryption-key
CREDENTIALS_ENCRYPTION_KEY_STAGING=your-staging-credentials-key
```

**Production Environment Secrets:**
```
BINANCE_API_KEY_PROD=your-production-binance-api-key
BINANCE_SECRET_KEY_PROD=your-production-binance-secret-key
JWT_SECRET_PROD=your-production-jwt-secret
ENCRYPTION_KEY_PROD=your-production-encryption-key
CREDENTIALS_ENCRYPTION_KEY_PROD=your-production-credentials-key
```

**Additional API Keys:**
```
GROQ_API_KEY=your-groq-api-key
SONAR_TOKEN=your-sonarcloud-token (optional)
GITLEAKS_LICENSE=your-gitleaks-license (optional)
```

### 2. Environment Protection Rules

#### Staging Environment
1. Go to Settings → Environments
2. Create environment: `staging`
3. No protection rules needed (automatic deployment)

#### Production Approval Environment
1. Create environment: `production-approval`
2. Add required reviewers (DevOps team members)
3. Set deployment branches: `main` only

#### Production Environment
1. Create environment: `production`
2. Add required reviewers (Senior developers)
3. Set deployment branches: `main` only
4. Add environment URL: `https://your-production-domain.com`

### 3. Branch Protection Rules

Configure branch protection for `main` branch:
- Require pull request reviews (2 reviewers)
- Require status checks:
  - `Enhanced CI Pipeline / Code Quality & Linting`
  - `Enhanced CI Pipeline / Unit Tests & Coverage`
  - `Enhanced CI Pipeline / Build Verification`
  - `Enhanced Security Scan / Dependency Scan`

## 🚀 CI/CD Pipeline Configuration

### Pipeline Overview

The FluxTrader CI/CD pipeline consists of three main workflows:

1. **Enhanced CI Pipeline** (`ci-enhanced.yml`)
   - Triggers: Push/PR to main/master/develop
   - Features: Code quality, testing, security scanning, AWS integration

2. **AWS Staging Deployment** (`cd-staging-aws.yml`)
   - Triggers: Push to main/master
   - Features: Automatic deployment to staging with AWS integration

3. **AWS Production Deployment** (`cd-production-aws.yml`)
   - Triggers: Manual workflow dispatch only
   - Features: Manual approval, blue-green deployment, rollback capabilities

### Workflow Features

#### Enhanced CI Pipeline
- ✅ **Intelligent Caching**: Dependency caching for faster builds
- ✅ **Parallel Execution**: Multiple jobs run simultaneously
- ✅ **AWS Integration**: Tests AWS Secrets Manager connectivity
- ✅ **Multi-Python Testing**: Tests on Python 3.11 and 3.12
- ✅ **Comprehensive Security**: Bandit, safety, secrets scanning
- ✅ **Container Security**: Docker image vulnerability scanning

#### AWS Staging Deployment
- ✅ **Infrastructure Management**: Automatic EC2/RDS provisioning
- ✅ **Secrets Management**: AWS Secrets Manager integration
- ✅ **Health Monitoring**: Comprehensive health checks
- ✅ **Rollback Capability**: Automatic failure recovery

#### AWS Production Deployment
- ✅ **Manual Approval**: Required human approval gate
- ✅ **Blue-Green Deployment**: Zero-downtime deployments
- ✅ **Enhanced Monitoring**: Extended stability verification
- ✅ **Emergency Rollback**: Automatic failure recovery

## 📊 Deployment Process

### Staging Deployment

Staging deployments are **automatic** when code is pushed to the main branch:

1. **Trigger**: Push to `main` branch
2. **CI Pipeline**: Runs enhanced CI pipeline
3. **Infrastructure**: Provisions/updates AWS resources
4. **Secrets**: Updates AWS Secrets Manager
5. **Deployment**: Deploys to EC2 instance
6. **Verification**: Health checks and smoke tests
7. **Monitoring**: Post-deployment stability monitoring

### Production Deployment

Production deployments are **manual** and require approval:

1. **Trigger**: Manual workflow dispatch
2. **Input Required**:
   - Version to deploy (e.g., `v20240815-abc1234`)
   - Staging validation confirmation
   - Emergency deployment flag (optional)

3. **Process**:
   ```bash
   # Navigate to GitHub Actions
   # Select "Deploy to AWS Production" workflow
   # Click "Run workflow"
   # Fill in required inputs:
   # - Version: v20240815-abc1234
   # - Staging validation: ✓
   # - Emergency deploy: (leave unchecked)
   ```

4. **Approval Gate**: Manual approval required
5. **Infrastructure**: Provisions/updates production AWS resources
6. **Backup**: Creates pre-deployment AMI backup
7. **Deployment**: Blue-green deployment strategy
8. **Verification**: Extended health checks and monitoring
9. **Rollback**: Automatic rollback on failure

### Emergency Deployment

For critical fixes, use emergency deployment:

1. **Trigger**: Manual workflow dispatch with emergency flag
2. **Skips**: Some validation checks for faster deployment
3. **Approval**: Can skip manual approval if needed
4. **Monitoring**: Enhanced monitoring and alerting

## 📊 Monitoring and Maintenance

### CloudWatch Integration

The deployment automatically configures CloudWatch monitoring:

#### Log Groups
- `/fluxtrader/staging/system` - System logs
- `/fluxtrader/staging/trading` - Trading session logs
- `/fluxtrader/staging/audit` - Audit logs (production)
- `/fluxtrader/staging/security` - Security logs (production)

#### Metrics
- **CPU Utilization**: Instance CPU usage
- **Memory Usage**: Memory consumption
- **Disk Usage**: Storage utilization
- **Network**: Network I/O metrics

### Health Monitoring

#### Automated Health Checks
- **Staging**: Every 5 minutes
- **Production**: Every 2 minutes
- **Endpoints**: `/health`, `/metrics`
- **Alerts**: Automatic notifications on failure

#### Manual Health Verification
```bash
# Check application health
curl -f http://your-instance-ip:8000/health

# Check metrics endpoint
curl -f http://your-instance-ip:8000/metrics

# Check container status
ssh -i your-key.pem ec2-user@your-instance-ip
docker ps | grep fluxtrader
```

### Backup Strategy

#### Automated Backups
- **Staging**: Daily backups (7-day retention)
- **Production**: Every 6 hours (30-day retention)
- **RDS**: Automatic backups enabled
- **AMI**: Pre-deployment snapshots

#### Manual Backup
```bash
# SSH to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Run backup script
/opt/fluxtrader/backup.sh

# Check backup status
ls -la /opt/fluxtrader/backups/
```

### Maintenance Tasks

#### Regular Maintenance
1. **Weekly**: Review CloudWatch logs and metrics
2. **Monthly**: Update dependencies and security patches
3. **Quarterly**: Review and rotate secrets
4. **Annually**: Review infrastructure costs and optimization

#### Security Updates
```bash
# Update system packages
sudo yum update -y

# Update Docker images
docker pull ghcr.io/your-username/kamikaze-be/fluxtrader:latest

# Restart application
sudo systemctl restart fluxtrader
```

## 🔧 Troubleshooting

### Common Issues

#### 1. CI Pipeline Failures

**Issue**: AWS Secrets Manager connection fails
```bash
# Solution: Check AWS credentials in GitHub secrets
# Verify IAM permissions for Secrets Manager access
```

**Issue**: Docker build fails
```bash
# Solution: Check Dockerfile syntax and dependencies
# Verify base image availability
```

#### 2. Deployment Failures

**Issue**: EC2 instance not accessible
```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx

# Verify instance state
aws ec2 describe-instances --instance-ids i-xxxxxxxxx
```

**Issue**: Application health checks fail
```bash
# SSH to instance and check logs
ssh -i your-key.pem ec2-user@your-instance-ip
sudo docker logs fluxtrader-staging

# Check application logs
tail -f /opt/fluxtrader/logs/system/health-check.log
```

#### 3. Database Connection Issues

**Issue**: Cannot connect to RDS
```bash
# Check RDS instance status
aws rds describe-db-instances --db-instance-identifier fluxtrader-staging

# Verify security group rules for port 5432
# Check secrets in AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id fluxtrader/staging/database/main
```

#### 4. Secrets Manager Issues

**Issue**: Secrets not found
```bash
# List all secrets
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `fluxtrader`)]'

# Create missing secrets
./scripts/deploy-infrastructure.sh --environment staging --secrets-only
```

### Debug Commands

#### Infrastructure Debugging
```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name fluxtrader-staging

# Check Terraform state
cd infrastructure/terraform
terraform show

# Check EC2 instance logs
aws logs get-log-events \
  --log-group-name /fluxtrader/staging/user-data \
  --log-stream-name i-xxxxxxxxx
```

#### Application Debugging
```bash
# SSH to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Check container status
docker ps -a

# View container logs
docker logs fluxtrader-staging

# Check application health
curl -v http://localhost:8000/health

# Check system resources
htop
df -h
free -m
```

### Support and Resources

#### Documentation Links
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

#### Getting Help
1. **GitHub Issues**: Report bugs and feature requests
2. **AWS Support**: For AWS-specific issues
3. **Community**: Join the FluxTrader community discussions

---

## 🎉 Conclusion

You now have a comprehensive, production-ready CI/CD pipeline for FluxTrader with:

- ✅ **Secure AWS Infrastructure**: EC2, RDS, Secrets Manager
- ✅ **Automated CI/CD**: Enhanced pipelines with security scanning
- ✅ **Secret Management**: AWS Secrets Manager integration
- ✅ **Monitoring**: CloudWatch logs and metrics
- ✅ **Backup Strategy**: Automated backups and snapshots
- ✅ **Security**: Multi-layered security controls
- ✅ **Scalability**: Production-ready infrastructure

The pipeline follows industry best practices for security, reliability, and maintainability, ensuring your FluxTrader deployment is robust and production-ready.

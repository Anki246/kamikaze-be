# Kamikaze AI Deployment Guide

This guide provides step-by-step instructions for deploying the Kamikaze AI backend using GitHub Actions.

## 🚀 Quick Start

### Prerequisites
- GitHub repository with the Kamikaze AI codebase
- AWS account with EC2 instance
- GitHub secrets configured

### 1. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

```
AWS_ACCESS_KEY_ID       # Your AWS access key
AWS_SECRET_ACCESS_KEY   # Your AWS secret key
AWS_REGION             # AWS region (e.g., us-east-1)
EC2_HOST               # EC2 public IP or hostname
EC2_USER               # EC2 username (ubuntu/ec2-user)
EC2_SSH_PRIVATE_KEY    # SSH private key (PEM format)
```

### 2. Trigger Deployment

#### Automatic Deployment
Push to the `dev` branch:
```bash
git push origin dev
```

#### Manual Deployment
1. Go to Actions tab in GitHub
2. Select "Deploy Kamikaze AI to AWS EC2"
3. Click "Run workflow"
4. Select branch and environment
5. Click "Run workflow"

### 3. Monitor Deployment

Watch the GitHub Actions logs for:
- ✅ Build completion
- ✅ Docker image creation
- ✅ EC2 deployment
- ✅ Health checks

## 🔧 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Run local troubleshooting
./scripts/troubleshoot-pipeline.sh
```

#### 2. SSH Connection Issues
- Check EC2 security groups (ports 22, 8000)
- Verify SSH key format (PEM)
- Ensure EC2 instance is running

#### 3. Docker Build Issues
```bash
# Test Docker build locally
docker build -t kamikaze-ai-test .
```

#### 4. Health Check Failures
```bash
# Verify deployment
./scripts/verify-deployment.sh [host] [port]
```

### Debug Commands

#### Check EC2 Instance
```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Check Docker containers
docker ps

# Check application logs
docker logs kamikaze-ai-backend

# Check system resources
df -h
free -h
```

#### Test Endpoints
```bash
# Health check
curl http://your-ec2-ip:8000/health

# Get authentication token
curl -X POST http://your-ec2-ip:8000/api/v1/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email": "demouser@kmkz.com", "password": "pass12345"}'

# Test authenticated endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://your-ec2-ip:8000/api/database/tables
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All GitHub secrets configured
- [ ] EC2 instance running and accessible
- [ ] Security groups configured (ports 22, 8000)
- [ ] Local tests passing

### During Deployment
- [ ] GitHub Actions workflow triggered
- [ ] Build job completed successfully
- [ ] Docker image created
- [ ] Files uploaded to EC2
- [ ] Container started successfully
- [ ] Health checks passing

### Post-Deployment
- [ ] Application accessible via browser
- [ ] Authentication working
- [ ] Database connectivity confirmed
- [ ] AWS services accessible
- [ ] Logs being generated

## 🔄 Workflow Overview

The deployment pipeline consists of:

1. **Build Job**
   - Syntax checks
   - Dependency installation
   - Docker image build
   - Basic container testing

2. **Deploy Job**
   - AWS credentials configuration
   - SSH key setup
   - File upload to EC2
   - Zero-downtime deployment
   - Health verification

3. **Cleanup Job**
   - Artifact cleanup
   - Old image removal

## 🛡️ Security Best Practices

- Use IAM roles instead of access keys when possible
- Rotate secrets regularly
- Use least privilege principle
- Monitor deployment logs
- Keep dependencies updated

## 📞 Support

If you encounter issues:

1. Run troubleshooting script: `./scripts/troubleshoot-pipeline.sh`
2. Check GitHub Actions logs
3. Verify EC2 instance status
4. Test local Docker build
5. Check application logs

For additional help, refer to:
- `GITHUB_SECRETS_SETUP.md`
- GitHub Actions workflow logs
- EC2 instance logs

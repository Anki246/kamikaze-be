# Kamikaze AI - GitHub Actions Deployment

This directory contains the GitHub Actions workflow for automated deployment of the Kamikaze AI backend to AWS EC2.

## 🚀 Deployment Workflow

The `deploy.yml` workflow provides:
- **Zero-downtime deployment** with health checks
- **Automatic rollback** on deployment failures
- **Docker containerization** with image caching
- **AWS Secrets Manager integration** for secure configuration
- **Multi-environment support** (production/staging)

## 📋 Prerequisites

### 1. AWS Infrastructure Setup

**EC2 Instance Requirements:**
- Ubuntu 20.04+ or Amazon Linux 2
- Docker installed and running
- Python 3.11+ installed
- Sufficient resources (minimum 2GB RAM, 2 vCPUs)
- Security groups allowing inbound traffic on port 8000

**AWS Secrets Manager:**
- `kmkz-db-secrets`: Database credentials
- `kmkz-app-secrets`: Application secrets (Groq API key, etc.)

**IAM Permissions:**
The deployment requires an IAM user/role with permissions for:
- Secrets Manager read access
- EC2 instance access (if using IAM roles)

### 2. GitHub Repository Secrets

Configure the following secrets in your GitHub repository:

#### Required Secrets
```
AWS_ACCESS_KEY_ID          # AWS access key for Secrets Manager
AWS_SECRET_ACCESS_KEY      # AWS secret key for Secrets Manager
AWS_REGION                 # AWS region (default: us-east-1)
EC2_HOST                   # EC2 instance public IP or hostname
EC2_USER                   # EC2 instance username (ubuntu/ec2-user)
EC2_SSH_PRIVATE_KEY        # Private SSH key for EC2 access
```

#### Optional Secrets
```
SLACK_WEBHOOK_URL          # Slack webhook for deployment notifications
```

### 3. EC2 Instance Setup

**Install Docker:**
```bash
# Ubuntu
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Amazon Linux 2
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

**Create Application Directory:**
```bash
sudo mkdir -p /opt/kamikaze-ai/{releases,shared/logs}
sudo chown -R $USER:$USER /opt/kamikaze-ai
```

**Install Required Tools:**
```bash
# Ubuntu
sudo apt install -y curl jq

# Amazon Linux 2
sudo yum install -y curl jq
```

## 🔧 Workflow Configuration

### Trigger Events

**Automatic Deployment:**
- Push to `main` branch triggers production deployment

**Manual Deployment:**
- Use "Run workflow" button in GitHub Actions
- Select environment (production/staging)

### Environment Variables

The workflow uses these environment variables:
- `APPLICATION_NAME`: kamikaze-ai
- `DOCKER_IMAGE_NAME`: kamikaze-ai-backend
- `HEALTH_CHECK_URL`: http://localhost:8000/health
- `DEPLOYMENT_TIMEOUT`: 300 seconds

## 📊 Deployment Process

### 1. Build Stage
- ✅ Checkout code and setup Python 3.11
- ✅ Install dependencies and run syntax checks
- ✅ Validate configuration files
- ✅ Build and test Docker image
- ✅ Upload Docker image as artifact

### 2. Deploy Stage
- ✅ Download Docker image artifact
- ✅ Configure AWS credentials
- ✅ Setup SSH connection to EC2
- ✅ Upload application files and Docker image
- ✅ Execute zero-downtime deployment script
- ✅ Verify deployment with health checks
- ✅ Update system services (nginx, systemd)
- ✅ Clean up old releases and Docker images

### 3. Cleanup Stage
- ✅ Remove temporary artifacts
- ✅ Send deployment notifications

## 🛡️ Security Features

### SSH Security
- Uses SSH key authentication
- Automatically adds EC2 host to known_hosts
- Secure file permissions (600) for private keys

### AWS Security
- Uses IAM credentials for AWS access
- Secrets stored in GitHub repository secrets
- AWS Secrets Manager for application secrets

### Container Security
- Non-root user in Docker container
- Resource limits and logging configuration
- Automatic restart policies

## 🔄 Zero-Downtime Deployment

The deployment process ensures zero downtime:

1. **Health Check**: Verify current service is healthy
2. **Backup**: Create backup of current deployment
3. **Deploy**: Start new container alongside existing one
4. **Verify**: Health check new container for 5 minutes
5. **Switch**: Replace old container with new one
6. **Cleanup**: Remove old container and releases

### Rollback Process

If deployment fails:
1. Stop new container
2. Restore backup deployment
3. Restart old container
4. Log failure details
5. Exit with error code

## 📝 Monitoring and Logging

### Health Checks
- Container status verification
- HTTP health endpoint check
- API functionality verification

### Logging
- Docker container logs with rotation
- Application logs in `/opt/kamikaze-ai/shared/logs`
- GitHub Actions workflow logs

### Notifications
- Deployment status notifications
- Slack integration (optional)
- GitHub commit status updates

## 🚨 Troubleshooting

### Common Issues

**SSH Connection Failed:**
```bash
# Check SSH key format
ssh-keygen -l -f ~/.ssh/id_rsa

# Test SSH connection
ssh -i ~/.ssh/id_rsa user@host
```

**Docker Permission Denied:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**Health Check Failed:**
```bash
# Check container logs
docker logs kamikaze-ai-backend

# Check application logs
tail -f /opt/kamikaze-ai/shared/logs/system/*.log
```

**AWS Secrets Access Denied:**
```bash
# Test AWS credentials
aws secretsmanager get-secret-value --secret-id kmkz-db-secrets
```

### Manual Rollback

If automatic rollback fails:
```bash
# Stop current container
docker stop kamikaze-ai-backend

# List available releases
ls -la /opt/kamikaze-ai/releases/

# Rollback to previous release
cd /opt/kamikaze-ai/releases/PREVIOUS_SHA
./deploy.sh
```

## 📚 Additional Resources

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Kamikaze AI Backend Documentation](../../README.md)

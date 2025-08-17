# FluxTrader Backend - Production Deployment Guide

## 🚀 Production Environment Configuration

### **Target Infrastructure**
- **EC2 Instance**: i-08bc5befe61de1a51
- **Instance Name**: kmkz-ec2
- **Public IP**: 3.81.64.108
- **Private IP**: 172.31.36.119
- **Key Pair**: kmkz-new-ec2key.pem
- **Database**: kmkz-database-new (AWS RDS PostgreSQL)
- **Database Migration**: Automated from localhost to RDS
- **Credentials**: Stored in GitHub secrets (Production environment)

---

## 🔧 **Configuration Changes Made**

### **1. AWS Secrets Manager Integration**
- ✅ Enhanced `src/infrastructure/database_config.py` to use AWS Secrets Manager
- ✅ Automatic fallback to environment variables for development
- ✅ SSL/TLS enabled for RDS connections
- ✅ Retrieves credentials from `kmkz-secrets` secret

### **2. Docker Production Configuration**
- ✅ Updated `Dockerfile` for production deployment
- ✅ Non-root user execution for security
- ✅ AWS SDK (boto3) included for Secrets Manager
- ✅ Production environment variables configured
- ✅ Health checks with proper startup time

### **3. Deployment Scripts**
- ✅ `scripts/deploy-to-ec2.sh` - Automated EC2 deployment
- ✅ `scripts/health-check.sh` - Comprehensive health monitoring
- ✅ Both scripts are executable and production-ready

### **4. Enhanced Health Monitoring**
- ✅ `/health` - Comprehensive service status
- ✅ `/health/database` - Database connectivity check
- ✅ `/health/aws` - AWS services status
- ✅ Real-time monitoring of all critical services

### **5. CI/CD Pipeline Integration**
- ✅ Added EC2 deployment job for main branch
- ✅ AWS credentials configuration
- ✅ SSH key setup for EC2 access
- ✅ Automated health checks post-deployment

---

## 🔐 **Required GitHub Secrets**

Add these secrets to your GitHub repository:

```
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
EC2_SSH_PRIVATE_KEY=<your-ec2-private-key>
```

---

## 🚀 **Deployment Process**

### **Automatic Deployment (Recommended)**
1. Push changes to `main` branch
2. GitHub Actions will automatically deploy to EC2
3. Monitor deployment at: https://github.com/Anki246/kamikaze-be/actions

### **Manual Deployment**
```bash
# Make scripts executable
chmod +x scripts/deploy-to-ec2.sh scripts/health-check.sh

# Deploy to EC2
./scripts/deploy-to-ec2.sh

# Run health checks
./scripts/health-check.sh
```

---

## 🏥 **Health Check Endpoints**

After deployment, verify services at:

- **Basic Health**: http://34.238.167.174:8000/health
- **Database Health**: http://34.238.167.174:8000/health/database
- **AWS Services**: http://34.238.167.174:8000/health/aws
- **API Documentation**: http://34.238.167.174:8000/docs

---

## 🔧 **Environment Variables**

### **Production Environment**
```bash
ENVIRONMENT=production
USE_AWS_SECRETS=true
AWS_DEFAULT_REGION=us-east-1
PYTHONPATH=/app/src
PYTHONUNBUFFERED=1
```

### **Database Configuration**
- Automatically retrieved from AWS Secrets Manager (`kmkz-secrets`)
- SSL/TLS encryption enabled for RDS connections
- Connection pooling optimized for production

---

## 🛡️ **Security Features**

- ✅ **AWS Secrets Manager**: Secure credential storage
- ✅ **SSL/TLS**: Encrypted database connections
- ✅ **Non-root containers**: Enhanced security
- ✅ **IAM roles**: Proper AWS permissions
- ✅ **No secrets in code**: All credentials externalized

---

## 📊 **Monitoring and Logging**

### **Application Logs**
```bash
# View container logs
docker logs fluxtrader-app

# Follow logs in real-time
docker logs -f fluxtrader-app
```

### **Container Status**
```bash
# Check container status
docker ps -f name=fluxtrader-app

# Container resource usage
docker stats fluxtrader-app
```

---

## 🔄 **Troubleshooting**

### **Common Issues**

1. **Database Connection Failed**
   - Check AWS Secrets Manager permissions
   - Verify RDS security groups allow EC2 access
   - Check health endpoint: `/health/database`

2. **AWS Secrets Manager Access Denied**
   - Verify EC2 IAM role has SecretsManager permissions
   - Check AWS region configuration
   - Check health endpoint: `/health/aws`

3. **Container Won't Start**
   - Check Docker logs: `docker logs fluxtrader-app`
   - Verify environment variables
   - Check port availability: `netstat -tlnp | grep 8000`

### **Manual Container Management**
```bash
# Stop container
docker stop fluxtrader-app

# Remove container
docker rm fluxtrader-app

# Rebuild and restart
docker build -t fluxtrader:latest .
docker run -d --name fluxtrader-app --restart unless-stopped -p 8000:8000 fluxtrader:latest
```

---

## ✅ **Deployment Verification**

After deployment, verify:

1. **Application Health**: http://34.238.167.174:8000/health
2. **Database Connectivity**: Check health endpoint shows RDS connection
3. **AWS Integration**: Verify secrets are loaded from AWS
4. **API Functionality**: Test endpoints at http://34.238.167.174:8000/docs

---

## 📞 **Support**

For deployment issues:
1. Check GitHub Actions logs
2. Review container logs on EC2
3. Verify AWS permissions and connectivity
4. Use health check endpoints for diagnostics

**Production URL**: http://34.238.167.174:8000
**Health Check**: http://34.238.167.174:8000/health
**API Docs**: http://34.238.167.174:8000/docs

# 🗄️ AWS RDS Migration Guide - Kamikaze-be

## 📋 **Overview**

This guide covers the migration from localhost PostgreSQL to AWS RDS database for the Kamikaze-be backend application.

## 🎯 **Migration Objectives**

✅ **Completed:**
- Database configuration updated to prioritize RDS over localhost
- Automatic migration script created (`scripts/migrate-to-rds.py`)
- GitHub Actions workflow updated to use RDS credentials
- Deployment script configured for RDS in production
- SSL configuration for secure RDS connections

## 🏗️ **Infrastructure Setup**

### **Current Configuration**
- **EC2 Instance**: i-08bc5befe61de1a51 (kmkz-ec2)
- **Public IP**: 3.81.64.108
- **RDS Database**: kmkz-database-new
- **GitHub Secrets**: Configured in Production environment

### **Database Environments**
- **Development**: localhost PostgreSQL (for local development)
- **Production**: AWS RDS PostgreSQL (for deployed application)

## 🔧 **Migration Process**

### **Automatic Migration (GitHub Actions)**

The migration runs automatically during deployment:

1. **Trigger**: Push to main branch
2. **Migration Step**: Runs `scripts/migrate-to-rds.py`
3. **Deployment**: Uses RDS credentials for application
4. **Verification**: Health checks confirm RDS connectivity

### **Manual Migration (Local)**

To run migration manually:

```bash
# Set RDS credentials
export DB_HOST='your-rds-endpoint.rds.amazonaws.com'
export DB_USER='your-rds-username'
export DB_PASSWORD='your-rds-password'
export DB_NAME='kamikaze'
export DB_PORT='5432'

# Optional: Override local database settings
export LOCAL_DB_NAME='kamikaze'
export LOCAL_DB_USER='postgres'
export LOCAL_DB_PASSWORD='admin2025'

# Run migration
python scripts/migrate-to-rds.py
```

Or use the helper script:
```bash
./scripts/setup-rds-migration.sh
```

## 📊 **Migration Features**

### **Data Migration**
- ✅ Schema creation (tables, indexes)
- ✅ Data transfer with batch processing
- ✅ Sequence reset for auto-increment columns
- ✅ Data verification and row count validation
- ✅ Comprehensive error handling and logging

### **Safety Features**
- ✅ Connection validation before migration
- ✅ Rollback capabilities
- ✅ Detailed logging with timestamps
- ✅ Non-destructive verification
- ✅ Graceful error handling

## 🔐 **Security Configuration**

### **SSL/TLS**
- RDS connections use SSL (`ssl_mode: require`)
- Automatic SSL detection for `.rds.amazonaws.com` hosts
- Secure credential handling via GitHub secrets

### **Credentials Management**
- Production credentials stored in GitHub secrets
- Environment-based configuration
- No hardcoded credentials in code

## 🚀 **Deployment Workflow**

### **GitHub Actions Steps**
1. **Setup**: Install dependencies, configure SSH
2. **Migration**: Run database migration to RDS
3. **Build**: Create Docker image with RDS configuration
4. **Deploy**: Deploy to EC2 with RDS connection
5. **Verify**: Health checks and connectivity tests

### **Environment Variables (Production)**
```yaml
ENVIRONMENT: production
GITHUB_ACTIONS: true
USE_AWS_SECRETS: false
DB_HOST: ${{ secrets.DB_HOST }}
DB_PORT: ${{ secrets.DB_PORT }}
DB_NAME: ${{ secrets.DB_NAME }}
DB_USER: ${{ secrets.DB_USER }}
DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

## 🧪 **Testing & Verification**

### **Migration Verification**
- Row count comparison between source and target
- Schema validation
- Connection testing
- Application health checks

### **Application Testing**
- API endpoint testing
- Database connectivity verification
- Performance monitoring
- Error logging review

## 📁 **File Structure**

```
scripts/
├── migrate-to-rds.py          # Main migration script
├── setup-rds-migration.sh     # Helper setup script
└── deploy-to-ec2.sh           # Updated deployment script

src/infrastructure/
├── database_config.py         # Updated for RDS priority
├── auth_database.py           # Lazy-loaded configuration
└── credentials_database.py    # Lazy-loaded configuration

.github/workflows/
└── ci-enhanced.yml            # Updated for RDS deployment
```

## 🔗 **Important URLs**

- **GitHub Repository**: https://github.com/Anki246/kamikaze-be
- **GitHub Actions**: https://github.com/Anki246/kamikaze-be/actions
- **GitHub Secrets**: https://github.com/Anki246/kamikaze-be/settings/secrets/actions
- **Application URL**: http://3.81.64.108:8000
- **Health Check**: http://3.81.64.108:8000/health

## 🚨 **Troubleshooting**

### **Common Issues**

**Migration Fails**
```bash
# Check RDS connectivity
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://user:pass@host:5432/db'))"

# Check migration logs
ls -la migration_*.log
tail -f migration_*.log
```

**Application Can't Connect to RDS**
```bash
# Verify environment variables in container
docker exec kamikaze-app env | grep DB_

# Check application logs
docker logs kamikaze-app
```

**GitHub Actions Deployment Fails**
- Verify GitHub secrets are set in Production environment
- Check workflow logs for specific error messages
- Ensure RDS security groups allow EC2 access

### **Recovery Steps**

1. **Rollback to localhost**: Remove RDS environment variables
2. **Re-run migration**: Use `python scripts/migrate-to-rds.py`
3. **Manual verification**: Connect to RDS and verify data
4. **Redeploy**: Push to main branch to trigger new deployment

## 📋 **Next Steps**

1. ✅ **Update GitHub Secrets**: Ensure RDS credentials are configured
2. ✅ **Test Migration**: Run migration script locally first
3. ✅ **Deploy via GitHub Actions**: Push to main branch
4. ✅ **Verify Application**: Test all endpoints with RDS
5. ✅ **Monitor Performance**: Check logs and metrics

## 🎉 **Success Criteria**

- ✅ Application connects to RDS database
- ✅ All data migrated successfully
- ✅ GitHub Actions deployment works
- ✅ Health checks pass
- ✅ API endpoints functional
- ✅ No localhost dependencies in production

The migration is designed to be seamless and automated, with comprehensive error handling and verification steps.

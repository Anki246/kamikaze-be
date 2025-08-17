# 🚀 CI/CD Pipeline Structure - Kamikaze-be

## 📋 **Pipeline Overview**

This document explains the CI/CD pipeline structure and which workflows run for different branches.

## 🔄 **Active Workflows**

### **1. 🧪 Dev Branch Deployment** 
- **File**: `.github/workflows/cd-dev-branch.yml`
- **Triggers**: 
  - Push to `dev`, `develop`, `development` branches
  - Pull requests to dev branches
  - Manual workflow dispatch
- **Purpose**: Development testing and validation
- **Target**: Current EC2 instance (i-08bc5befe61de1a51) with RDS
- **Environment**: `development`
- **Features**:
  - ✅ Build and test application
  - ✅ Run database migration to RDS
  - ✅ Deploy to EC2 with RDS configuration
  - ✅ Health checks and smoke tests
  - ✅ Database connection verification

### **2. 🚀 Production Deployment**
- **File**: `.github/workflows/ci-enhanced.yml`
- **Triggers**: 
  - Push to `main`, `master` branches
  - Pull requests to main branches
  - Manual workflow dispatch
- **Purpose**: Production deployment
- **Target**: EC2 instance with RDS (production environment)
- **Environment**: `production`
- **Features**:
  - ✅ Comprehensive CI/CD pipeline
  - ✅ Security scanning
  - ✅ Production deployment
  - ✅ AWS integration

## 🚫 **Disabled Workflows**

### **3. 🚀 Deploy to AWS Staging** (DISABLED)
- **File**: `.github/workflows/cd-staging-aws.yml`
- **Status**: **DISABLED** to avoid conflicts
- **Reason**: This was an old staging setup that conflicted with the current dev branch workflow
- **Replacement**: Use `cd-dev-branch.yml` for development testing

## 🎯 **Branch Strategy**

### **Development Workflow**
```
dev branch → cd-dev-branch.yml → EC2 (development environment)
```

1. **Push to dev branch**
2. **Triggers**: `🧪 Deploy to Dev Branch` workflow
3. **Steps**:
   - Build and test
   - Database migration (localhost → RDS)
   - Deploy to EC2
   - Health checks
   - Smoke tests

### **Production Workflow**
```
main branch → ci-enhanced.yml → EC2 (production environment)
```

1. **Merge dev → main**
2. **Triggers**: `🚀 Enhanced CI Pipeline with AWS Integration`
3. **Steps**:
   - Full CI/CD pipeline
   - Security scanning
   - Production deployment
   - Monitoring setup

## 🔧 **Current Setup Details**

### **Infrastructure**
- **EC2 Instance**: i-08bc5befe61de1a51 (kmkz-ec2)
- **Public IP**: 3.81.64.108
- **Database**: AWS RDS (kmkz-database-new)
- **SSH Key**: kmkz-new-ec2key.pem

### **Environment Secrets**

#### **Development Environment**
- `EC2_SSH_PRIVATE_KEY` - SSH key for EC2 access
- `DB_HOST` - RDS endpoint
- `DB_PORT` - Database port (5432)
- `DB_NAME` - Database name
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password

#### **Production Environment**
- Same as development + additional production secrets

## 🚀 **How to Deploy**

### **For Development Testing**
```bash
# Work on dev branch
git checkout dev
git add .
git commit -m "your changes"
git push origin dev
```

**Result**: Triggers `🧪 Deploy to Dev Branch` workflow

### **For Production Deployment**
```bash
# Merge dev to main after testing
git checkout main
git merge dev
git push origin main
```

**Result**: Triggers `🚀 Enhanced CI Pipeline with AWS Integration` workflow

## 📊 **Monitoring Deployments**

### **GitHub Actions URLs**
- **All Workflows**: https://github.com/Anki246/kamikaze-be/actions
- **Dev Deployments**: Filter by "🧪 Deploy to Dev Branch"
- **Production Deployments**: Filter by "🚀 Enhanced CI Pipeline"

### **Application URLs**
- **Development**: http://3.81.64.108:8000
- **Health Check**: http://3.81.64.108:8000/health
- **API Docs**: http://3.81.64.108:8000/docs

## 🔍 **Troubleshooting**

### **Multiple Workflows Running**
If you see multiple workflows running for the same commit:
1. Check which branch triggered them
2. Only `cd-dev-branch.yml` should run for dev branch
3. Only `ci-enhanced.yml` should run for main branch
4. `cd-staging-aws.yml` is disabled and should not run

### **Workflow Conflicts**
- ✅ **Fixed**: Main CI pipeline no longer runs on dev branch
- ✅ **Fixed**: Staging workflow disabled
- ✅ **Result**: Clean separation between dev and production pipelines

## 📋 **Summary**

### **Current Active Pipelines**
1. **Dev Branch** → `cd-dev-branch.yml` → Development testing
2. **Main Branch** → `ci-enhanced.yml` → Production deployment

### **Key Benefits**
- ✅ Clear separation of dev and production
- ✅ No workflow conflicts
- ✅ RDS integration in both environments
- ✅ Comprehensive testing and validation
- ✅ Automated database migration

### **Recommended Workflow**
1. Develop and test on `dev` branch
2. Monitor dev deployment success
3. Merge to `main` for production deployment
4. Monitor production deployment

This structure ensures clean, predictable deployments with proper testing before production.

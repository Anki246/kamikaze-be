# 🚀 CI/CD Pipeline Structure - Kamikaze-be

## 📋 **Pipeline Overview**

This document explains the unified CI/CD pipeline structure that handles all branches and environments in a single workflow.

## 🔄 **Single Unified Pipeline**

### **🚀 Kamikaze-be CI/CD Pipeline**
- **File**: `.github/workflows/ci-enhanced.yml`
- **Triggers**:
  - Push to `main`, `master`, `dev`, `develop`, `cicd-be` branches
  - Pull requests to these branches
  - Manual workflow dispatch with branch selection
- **Purpose**: Complete CI/CD for all environments
- **Target**: EC2 instance (i-08bc5befe61de1a51) with RDS
- **Features**:
  - ✅ Branch detection and environment mapping
  - ✅ Manual approval for production/staging branches
  - ✅ Automatic deployment for dev branches
  - ✅ Database migration (localhost → RDS)
  - ✅ SSH-based EC2 deployment
  - ✅ Health checks and verification
  - ✅ Comprehensive CI/CD pipeline
  - ✅ Security scanning
  - ✅ Multi-environment support

## 🎯 **Branch Strategy & Approval Flow**

### **Branch-to-Environment Mapping**
```
dev/develop     → development environment (auto-deploy)
cicd-be         → staging environment (manual approval)
main/master     → production environment (manual approval)
```

### **Approval Requirements**
- **Dev Branch**: ✅ **Auto-deploy** (no approval needed)
- **CICD-be Branch**: 🔐 **Manual approval required**
- **Main Branch**: 🔐 **Manual approval required**

### **Workflow Steps**
1. **Branch Detection**: Automatically detects branch and sets environment
2. **Approval Gate**: Waits for manual approval (if required)
3. **CI Pipeline**: Build, test, security scan
4. **Database Migration**: Migrate data from localhost to RDS
5. **EC2 Deployment**: Deploy via SSH to EC2 instance
6. **Health Checks**: Verify application is running
7. **Summary**: Generate deployment report

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

### **For Development Testing (Auto-Deploy)**
```bash
# Work on dev branch
git checkout dev
git add .
git commit -m "your changes"
git push origin dev
```

**Result**: Automatically deploys to development environment (no approval needed)

### **For Staging Deployment (Manual Approval)**
```bash
# Work on cicd-be branch
git checkout cicd-be
git add .
git commit -m "your changes"
git push origin cicd-be
```

**Result**: Triggers pipeline with manual approval gate for staging environment

### **For Production Deployment (Manual Approval)**
```bash
# Merge to main after testing
git checkout main
git merge dev  # or cicd-be
git push origin main
```

**Result**: Triggers pipeline with manual approval gate for production environment

### **Manual Workflow Dispatch**
You can also trigger deployments manually from GitHub Actions:
1. Go to Actions → Kamikaze-be CI/CD Pipeline
2. Click "Run workflow"
3. Select target branch and environment
4. Choose whether to require approval

## 📊 **Monitoring Deployments**

### **GitHub Actions URLs**
- **All Workflows**: https://github.com/Anki246/kamikaze-be/actions
- **Unified Pipeline**: Filter by "🚀 Kamikaze-be CI/CD Pipeline"
- **Manual Trigger**: https://github.com/Anki246/kamikaze-be/actions/workflows/ci-enhanced.yml

### **Application URLs**
- **Development**: http://3.81.64.108:8000
- **Health Check**: http://3.81.64.108:8000/health
- **API Docs**: http://3.81.64.108:8000/docs

## 🔍 **Troubleshooting**

### **Single Pipeline Benefits**
- ✅ **No Conflicts**: Only one workflow runs per commit
- ✅ **Unified Logic**: All environments handled in one place
- ✅ **Clear Approval Flow**: Manual approval for production/staging
- ✅ **Auto-Deploy Dev**: Development changes deploy automatically

## 📋 **Summary**

### **Single Unified Pipeline**
- **All Branches** → `ci-enhanced.yml` → Environment-specific deployment

### **Key Benefits**
- ✅ Single source of truth for all deployments
- ✅ Consistent CI/CD logic across environments
- ✅ Manual approval gates for production safety
- ✅ Automatic dev deployments for fast iteration
- ✅ RDS integration with database migration
- ✅ SSH-based EC2 deployment
- ✅ Comprehensive testing and security scanning

### **Recommended Workflow**
1. **Develop**: Work on `dev` branch → auto-deploy to development
2. **Stage**: Test on `cicd-be` branch → manual approval for staging
3. **Production**: Merge to `main` → manual approval for production
4. **Monitor**: Use GitHub Actions and application URLs to verify

This unified structure ensures consistent, secure deployments with appropriate approval gates.

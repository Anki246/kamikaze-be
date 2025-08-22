# Simplified CI/CD Pipeline

This directory contains the simplified CI/CD workflows for the Kamikaze AI Trading Bot.

## Overview

The pipeline consists of just **2 essential workflows**:

### 1. CI Pipeline (`ci.yml`) - Continuous Integration
**Triggers:** Push to `main`/`dev`/`develop`, Pull Requests

**What it does:**
- ✅ **Code Quality Checks** - Black formatting, isort, Flake8 linting
- ✅ **Security Scanning** - Bandit security analysis
- ✅ **Testing** - Pytest with coverage reporting
- ✅ **Docker Build** - Container image creation and testing
- ✅ **Validation** - Configuration and project structure checks

**Jobs:**
1. **Test** - Multi-Python version testing (3.11, 3.12)
2. **Build** - Docker image creation and validation
3. **Validate** - Final configuration and structure validation

### 2. CD Pipeline (`cd.yml`) - Continuous Deployment
**Triggers:** Successful CI on `main` or `dev` branch

**What it does:**
- 🚀 **Staging Deployment** - Automatic deployment to staging
- 🧪 **Smoke Tests** - Basic functionality validation
- 🏭 **Production Deployment** - Manual approval required
- 📦 **Container Registry** - Push images to GitHub Container Registry
- 🏷️ **Release Creation** - Automatic GitHub releases
- 🔄 **Rollback** - Automatic rollback on failure

**Jobs:**
1. **Deploy Staging** - Automatic staging deployment
2. **Deploy Production** - Manual production deployment (requires approval)
3. **Rollback** - Automatic rollback on failure

## Environment Configuration

### Staging Environment
- **URL:** `https://staging.kamikaze-ai.com` (main) / `https://dev-staging.kamikaze-ai.com` (dev)
- **Deployment:** Automatic on main or dev branch
- **Approval:** Not required
- **Testing:** Smoke tests included

### Production Environment
- **URL:** `https://kamikaze-ai.com`
- **Deployment:** Manual approval required
- **Approval:** 1 reviewer, 5-minute wait timer
- **Testing:** Full production validation

## Required Setup

### 1. GitHub Secrets
The pipeline uses minimal secrets:
- `GITHUB_TOKEN` - Automatically provided by GitHub

### 2. Environment Protection Rules
Configure in GitHub repository settings:
- **Staging:** No protection rules
- **Production:** Require reviewers, deployment branch restrictions

## Features

### ✅ **Simplified Architecture**
- Only 2 workflow files (vs 4+ in complex setups)
- Clear separation of CI and CD concerns
- Easy to understand and maintain

### ✅ **Comprehensive Testing**
- Multi-Python version support
- Code quality enforcement
- Security scanning included
- Docker container testing

### ✅ **Smart Deployment**
- Staging-first deployment strategy
- Manual production approval
- Automatic rollback on failure
- Container registry integration

### ✅ **Built-in Safety**
- Health checks at each stage
- Smoke tests before production
- Rollback capability
- Environment isolation

## Usage

### For Developers
1. **Create Pull Request** → CI pipeline runs automatically
2. **Merge to dev** → CD pipeline deploys to dev-staging environment
3. **Merge to main** → CD pipeline deploys to staging, then production (with approval)

### For DevOps
1. **Monitor CI results** in GitHub Actions tab
2. **Approve production deployments** when ready
3. **Check deployment status** in environments tab

## Validation

Run the validation script to ensure everything is set up correctly:

```bash
./scripts/validate-simple-pipeline.sh
```

This will check:
- ✅ Workflow files exist and have valid syntax
- ✅ Environment configurations are present
- ✅ Project structure is correct
- ✅ Basic tests can run

## Benefits of Simplified Pipeline

### 🎯 **Focused**
- Only essential workflows
- Clear responsibilities
- Reduced complexity

### 🚀 **Fast**
- Streamlined processes
- Parallel job execution
- Efficient resource usage

### 🔧 **Maintainable**
- Easy to understand
- Simple to modify
- Clear documentation

### 💰 **Cost-Effective**
- Fewer workflow minutes used
- Optimized resource allocation
- Reduced maintenance overhead

## Troubleshooting

### CI Pipeline Issues
```bash
# Fix code formatting
black .
isort .

# Run tests locally
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/test_basic.py -v
```

### CD Pipeline Issues
- Check environment protection rules in GitHub
- Verify GITHUB_TOKEN permissions
- Review deployment logs in Actions tab

## Next Steps

1. **Configure environments** in GitHub repository settings
2. **Set up protection rules** for production environment
3. **Test the pipeline** with a pull request
4. **Monitor first deployment** to ensure everything works

The simplified pipeline provides all essential CI/CD functionality while being easy to understand and maintain!

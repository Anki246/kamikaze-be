# Kamikaze-be CI/CD Pipeline Setup Guide

## 🚀 **Automated Deployment via GitHub Actions**

Your CI/CD pipeline is configured to automatically deploy **Kamikaze-be** to your EC2 instance when you push to `dev` or `main` branches.

### **Current Configuration**
- **Application**: Kamikaze-be Backend
- **EC2 Instance**: i-07e35a954b57372a3 (34.238.167.174)
- **Container**: kamikaze-app
- **Port**: 8000
- **User**: ubuntu

---

## 🔑 **Required GitHub Secrets**

To enable automatic deployment, add these secrets to your GitHub repository:

### **Method 1: SSH Key Authentication (Recommended)**

1. **Generate SSH Key Pair** (if you don't have one):
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/kamikaze-ec2-key
   ```

2. **Add Public Key to EC2**:
   ```bash
   # Copy the public key
   cat ~/.ssh/kamikaze-ec2-key.pub
   
   # SSH to your EC2 and add it to authorized_keys
   ssh ubuntu@34.238.167.174
   echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

3. **Add Private Key to GitHub Secrets**:
   - Go to: **Repository** → **Settings** → **Secrets and variables** → **Actions**
   - Add secret: `EC2_SSH_PRIVATE_KEY`
   - Value: Content of `~/.ssh/kamikaze-ec2-key` (entire private key including headers)

### **Method 2: AWS Systems Manager (Alternative)**

If SSH keys are not available, the pipeline will automatically fall back to AWS Systems Manager.

Required secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

---

## 🔧 **Optional Database Secrets**

For custom database configuration (if not using defaults):

```
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=kamikaze
DB_USER=your-db-user
DB_PASSWORD=your-db-password
```

---

## 🚀 **Triggering Deployment**

### **Automatic Deployment**
```bash
# Any push to dev or main branch triggers deployment
git add .
git commit -m "deploy: update kamikaze-be application"
git push origin dev
```

### **Manual Deployment**
If you need to deploy manually:
```bash
# SSH to EC2 and run:
curl -s https://raw.githubusercontent.com/Anki246/kamikaze-be/dev/deployment_script.sh | bash
```

---

## 📊 **Pipeline Stages**

Your CI/CD pipeline includes:

1. **✅ Setup & Caching** - Environment preparation
2. **✅ Code Quality** - Linting and formatting
3. **✅ Unit Tests** - Application testing
4. **✅ Integration Tests** - Service integration
5. **✅ Docker Build** - Container creation
6. **✅ Security Scan** - Vulnerability checking
7. **🚀 EC2 Deployment** - Production deployment
8. **🏥 Health Check** - Deployment verification

---

## 🔍 **Monitoring Deployment**

### **GitHub Actions**
- Monitor at: https://github.com/Anki246/kamikaze-be/actions
- Check deployment logs and status

### **Application Health**
After deployment, verify:
- **Health**: http://34.238.167.174:8000/health
- **API Docs**: http://34.238.167.174:8000/docs
- **Root**: http://34.238.167.174:8000/

### **Container Status**
SSH to EC2 and check:
```bash
sudo docker ps -f name=kamikaze-app
sudo docker logs kamikaze-app
```

---

## 🛠️ **Troubleshooting**

### **Deployment Fails**
1. Check GitHub Actions logs
2. Verify SSH key is correct
3. Ensure security group allows port 8000
4. Check EC2 instance is running

### **Application Not Accessible**
1. Verify container is running: `sudo docker ps`
2. Check logs: `sudo docker logs kamikaze-app`
3. Test locally: `curl http://localhost:8000/health`
4. Check security group inbound rules

### **SSH Connection Issues**
1. Verify SSH key is added to EC2
2. Check EC2 security group allows SSH (port 22)
3. Pipeline will fall back to AWS SSM if SSH fails

---

## ✅ **Quick Setup Checklist**

- [ ] Security group allows inbound port 8000
- [ ] Security group allows inbound port 22 (for SSH)
- [ ] SSH key added to GitHub secrets (optional)
- [ ] AWS credentials added to GitHub secrets (optional)
- [ ] Repository has latest code
- [ ] Push to dev/main branch to trigger deployment

---

## 🎯 **Expected Results**

After successful deployment:

```bash
✅ Container: kamikaze-app running
✅ Port 8000: Accessible externally
✅ Health endpoint: Responding
✅ API docs: Available
✅ Auto-restart: Enabled
```

**Your Kamikaze-be application will be automatically deployed and accessible at:**
**http://34.238.167.174:8000** 🚀

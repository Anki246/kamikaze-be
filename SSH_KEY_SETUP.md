# SSH Key Setup for Kamikaze-be CI/CD Deployment

## 🔑 **Add SSH Key to GitHub Secrets**

To enable automatic deployment of Kamikaze-be to your EC2 instance, you need to add your SSH private key to GitHub secrets.

### **Step 1: Copy SSH Key Content**

Your SSH key is located at: `~/Downloads/kmkz-key-ec2.pem`

Copy the entire content of this file:

```bash
cat ~/Downloads/kmkz-key-ec2.pem
```

### **Step 2: Add to GitHub Secrets**

1. **Go to your GitHub repository**: https://github.com/Anki246/kamikaze-be
2. **Click**: Settings → Secrets and variables → Actions
3. **Click**: "New repository secret"
4. **Name**: `EC2_SSH_PRIVATE_KEY`
5. **Value**: Paste the entire content of your PEM file (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`)
6. **Click**: "Add secret"

### **Step 3: Trigger Deployment**

Once the secret is added, any push to `dev` or `main` branch will automatically deploy Kamikaze-be to your EC2 instance.

```bash
# Make any change and push to trigger deployment
git add .
git commit -m "trigger: deploy kamikaze-be to EC2"
git push origin dev
```

### **Step 4: Monitor Deployment**

- **GitHub Actions**: https://github.com/Anki246/kamikaze-be/actions
- **Expected URLs after deployment**:
  - Health: http://34.238.167.174:8000/health
  - API Docs: http://34.238.167.174:8000/docs
  - Root: http://34.238.167.174:8000/

---

## 🚀 **What Happens During Deployment**

1. **✅ Code Quality Checks** - Linting and formatting
2. **✅ Unit Tests** - Application testing  
3. **✅ Docker Build** - Container creation
4. **✅ Security Scan** - Vulnerability checking
5. **🚀 EC2 Deployment** - Deploy to your instance
6. **🏥 Health Check** - Verify deployment success

---

## 🔧 **Deployment Details**

- **Application**: Kamikaze-be Backend
- **Container**: kamikaze-app
- **Port**: 8000
- **Instance**: i-07e35a954b57372a3 (34.238.167.174)
- **User**: ubuntu (auto-detected)
- **Docker Image**: kamikaze-be:latest

---

## ✅ **Expected Results**

After successful deployment:

```bash
✅ Container: kamikaze-app running
✅ Port 8000: Accessible externally  
✅ Health endpoint: http://34.238.167.174:8000/health
✅ API docs: http://34.238.167.174:8000/docs
✅ Auto-restart: Enabled
```

---

## 🛠️ **Troubleshooting**

### **If Deployment Fails**
1. Check GitHub Actions logs for detailed error messages
2. Verify SSH key is correctly added to secrets
3. Ensure EC2 instance is running and accessible
4. Check security group allows port 8000 inbound

### **If Application Not Accessible**
1. Verify container is running: SSH to EC2 and run `sudo docker ps`
2. Check logs: `sudo docker logs kamikaze-app`
3. Test locally: `curl http://localhost:8000/health`
4. Verify security group inbound rules for port 8000

---

## 📞 **Quick Commands**

After deployment, you can SSH to your EC2 and run:

```bash
# Check container status
sudo docker ps -f name=kamikaze-app

# View logs
sudo docker logs kamikaze-app

# Test health locally
curl http://localhost:8000/health

# Restart container if needed
sudo docker restart kamikaze-app
```

**Ready to deploy? Add the SSH key to GitHub secrets and push to dev branch!** 🚀

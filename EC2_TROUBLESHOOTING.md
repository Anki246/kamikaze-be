# 🔧 EC2 Deployment Troubleshooting Guide

## 🚨 **Common SSH Connection Issues**

### **Issue: SSH connection fails during deployment**

**Error Message:**
```
❌ SSH connection test failed
⚠️ ssh-keyscan failed, will use StrictHostKeyChecking=no
```

### **Possible Causes & Solutions**

#### **1. EC2 Instance is Stopped**
**Check**: Instance state in AWS Console or GitHub Actions logs
**Solution**: The pipeline now automatically starts stopped instances

```bash
# Manual check via AWS CLI
aws ec2 describe-instances --instance-ids i-08bc5befe61de1a51 \
  --query 'Reservations[0].Instances[0].State.Name'
```

#### **2. Security Group Restrictions**
**Issue**: Security group doesn't allow SSH from GitHub Actions IP ranges
**Solution**: Update security group to allow SSH (port 22) from 0.0.0.0/0 or GitHub Actions IP ranges

**AWS Console Steps:**
1. Go to EC2 → Security Groups
2. Find security group for instance i-08bc5befe61de1a51
3. Edit inbound rules
4. Ensure SSH (port 22) is allowed from 0.0.0.0/0

#### **3. SSH Key Issues**
**Issue**: SSH key in GitHub secrets is incorrect or corrupted
**Solution**: Verify and update the SSH key

**Steps to fix:**
1. Check if you have the correct private key file (kmkz-new-ec2key.pem)
2. Verify key format:
   ```bash
   ssh-keygen -lf kmkz-new-ec2key.pem
   ```
3. Update GitHub secret `EC2_SSH_PRIVATE_KEY` with correct key content

#### **4. Public IP Changed**
**Issue**: EC2 instance has a different public IP
**Solution**: Update the IP in the pipeline or use Elastic IP

**Check current IP:**
```bash
aws ec2 describe-instances --instance-ids i-08bc5befe61de1a51 \
  --query 'Reservations[0].Instances[0].PublicIpAddress'
```

## 🔍 **Debugging Steps**

### **Step 1: Check Instance Status**
```bash
aws ec2 describe-instances --instance-ids i-08bc5befe61de1a51 \
  --query 'Reservations[0].Instances[0].{State:State.Name,PublicIP:PublicIpAddress,SecurityGroups:SecurityGroups[*].GroupId}'
```

### **Step 2: Test SSH Locally**
```bash
ssh -i ~/.ssh/kmkz-new-ec2key.pem ubuntu@3.81.64.108 "echo 'Connection test'"
```

### **Step 3: Check Security Groups**
```bash
aws ec2 describe-security-groups \
  --group-ids $(aws ec2 describe-instances --instance-ids i-08bc5befe61de1a51 \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
```

## 🛠️ **Quick Fixes**

### **Fix 1: Start EC2 Instance**
```bash
aws ec2 start-instances --instance-ids i-08bc5befe61de1a51
aws ec2 wait instance-running --instance-ids i-08bc5befe61de1a51
```

### **Fix 2: Update Security Group**
```bash
# Get security group ID
SG_ID=$(aws ec2 describe-instances --instance-ids i-08bc5befe61de1a51 \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

# Add SSH rule (if not exists)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0
```

### **Fix 3: Test SSH Key**
```bash
# Test SSH key format
ssh-keygen -lf kmkz-new-ec2key.pem

# Test connection
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
  -i kmkz-new-ec2key.pem ubuntu@3.81.64.108 "echo 'Test successful'"
```

## 📋 **GitHub Secrets Checklist**

Ensure these secrets are configured in your GitHub repository:

### **Required Secrets (Development Environment)**
- ✅ `EC2_SSH_PRIVATE_KEY` - Content of kmkz-new-ec2key.pem file
- ✅ `DB_HOST` - RDS endpoint
- ✅ `DB_PORT` - Database port (5432)
- ✅ `DB_NAME` - Database name
- ✅ `DB_USER` - Database username
- ✅ `DB_PASSWORD` - Database password
- ✅ `AWS_ACCESS_KEY_ID` - AWS access key
- ✅ `AWS_SECRET_ACCESS_KEY` - AWS secret key

### **How to Update SSH Key Secret**
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Find `EC2_SSH_PRIVATE_KEY` secret
3. Update with the complete content of your private key file:
   ```
   -----BEGIN RSA PRIVATE KEY-----
   [key content]
   -----END RSA PRIVATE KEY-----
   ```

## 🔄 **Pipeline Improvements**

The updated pipeline now includes:

### **Automatic EC2 Management**
- ✅ Checks EC2 instance state
- ✅ Automatically starts stopped instances
- ✅ Waits for instance to be ready

### **Enhanced Error Handling**
- ✅ Graceful handling of SSH connection failures
- ✅ Detailed error messages with troubleshooting hints
- ✅ Instance information gathering on failures

### **Robust SSH Setup**
- ✅ SSH key format validation
- ✅ Host key management with fallback
- ✅ Connection testing with retries

## 🆘 **Emergency Recovery**

### **If Deployment Completely Fails**
1. **Manual SSH**: Connect directly to EC2 instance
2. **Check Logs**: Review application logs on EC2
3. **Restart Services**: Manually restart Docker containers
4. **Rollback**: Deploy previous working version

### **Manual Deployment Commands**
```bash
# SSH to EC2
ssh -i kmkz-new-ec2key.pem ubuntu@3.81.64.108

# Check Docker status
sudo docker ps -a

# Restart application
sudo docker restart kamikaze-app

# Check logs
sudo docker logs kamikaze-app --tail 50
```

## 📞 **Getting Help**

If issues persist:
1. Check GitHub Actions logs for detailed error messages
2. Verify all GitHub secrets are correctly configured
3. Test SSH connection manually from your local machine
4. Check AWS Console for EC2 instance status and security groups
5. Review this troubleshooting guide for specific error patterns

The pipeline is designed to be resilient and provide clear error messages to help diagnose issues quickly.

# GitHub Secrets Configuration for FluxTrader Production Deployment

## 🔐 Required GitHub Secrets

To deploy FluxTrader to your EC2 instance with RDS database connectivity, you need to configure the following secrets in your GitHub repository.

### **How to Add Secrets**
1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

---

## 🚀 **AWS Configuration Secrets**

### **AWS_ACCESS_KEY_ID**
- **Description**: AWS access key for EC2 and Secrets Manager access
- **Value**: Your AWS access key ID
- **Example**: `AKIAIOSFODNN7EXAMPLE`

### **AWS_SECRET_ACCESS_KEY**
- **Description**: AWS secret access key
- **Value**: Your AWS secret access key
- **Example**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

---

## 🖥️ **EC2 Configuration Secrets**

### **EC2_SSH_PRIVATE_KEY**
- **Description**: Private SSH key for accessing EC2 instance
- **Value**: Your EC2 private key (entire content including headers)
- **Format**:
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...your private key content...
-----END RSA PRIVATE KEY-----
```

---

## 🗄️ **Database Configuration Secrets**

### **DB_HOST**
- **Description**: RDS database hostname
- **Value**: Your RDS endpoint
- **Example**: `kamikaze-db.cluster-xyz.us-east-1.rds.amazonaws.com`

### **DB_PORT**
- **Description**: Database port
- **Value**: `5432`

### **DB_NAME**
- **Description**: Database name
- **Value**: `kamikaze`

### **DB_USER**
- **Description**: Database username
- **Value**: Your RDS master username
- **Example**: `postgres`

### **DB_PASSWORD**
- **Description**: Database password
- **Value**: Your RDS master password
- **Security**: This should be a strong, unique password

---

## 🔧 **Optional Secrets (for enhanced functionality)**

### **GROQ_API_KEY**
- **Description**: Groq API key for AI/LLM functionality
- **Value**: Your Groq API key
- **Example**: `gsk_...`

### **BINANCE_API_KEY**
- **Description**: Binance API key for trading
- **Value**: Your Binance API key

### **BINANCE_SECRET_KEY**
- **Description**: Binance secret key for trading
- **Value**: Your Binance secret key

---

## ✅ **Verification**

After adding all secrets, your GitHub repository should have these secrets configured:

### **Required for Deployment**
- ✅ `AWS_ACCESS_KEY_ID`
- ✅ `AWS_SECRET_ACCESS_KEY`
- ✅ `EC2_SSH_PRIVATE_KEY`
- ✅ `DB_HOST`
- ✅ `DB_PORT`
- ✅ `DB_NAME`
- ✅ `DB_USER`
- ✅ `DB_PASSWORD`

### **Optional for Full Functionality**
- ⚪ `GROQ_API_KEY`
- ⚪ `BINANCE_API_KEY`
- ⚪ `BINANCE_SECRET_KEY`

---

## 🚀 **Deployment Process**

Once all required secrets are configured:

1. **Push to main branch** → Triggers automatic deployment
2. **GitHub Actions** → Uses secrets for secure deployment
3. **EC2 Deployment** → Application deployed with production configuration
4. **Health Check** → Verify deployment at http://34.238.167.174:8000/health

---

## 🛡️ **Security Best Practices**

### **Secret Management**
- ✅ **Never commit secrets to code**
- ✅ **Use GitHub secrets for all credentials**
- ✅ **Rotate secrets regularly**
- ✅ **Use least privilege AWS IAM policies**

### **Database Security**
- ✅ **Use strong, unique passwords**
- ✅ **Enable SSL/TLS for database connections**
- ✅ **Restrict database access to EC2 security group**
- ✅ **Regular security updates**

### **EC2 Security**
- ✅ **Use key-based SSH authentication**
- ✅ **Disable password authentication**
- ✅ **Keep SSH keys secure**
- ✅ **Regular security patches**

---

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Deployment fails with "Permission denied"**
   - Check AWS credentials have correct permissions
   - Verify EC2 SSH key is correct

2. **Database connection fails**
   - Verify DB_HOST points to correct RDS endpoint
   - Check RDS security group allows EC2 access
   - Confirm database credentials are correct

3. **Secrets not found**
   - Ensure all required secrets are added to GitHub
   - Check secret names match exactly (case-sensitive)

### **Testing Secrets**
```bash
# Test deployment locally (with proper AWS credentials)
./scripts/deploy-to-ec2.sh

# Check application health
./scripts/health-check.sh
```

---

## 📞 **Support**

If you encounter issues:
1. Check GitHub Actions logs for detailed error messages
2. Verify all secrets are correctly configured
3. Test database connectivity from EC2 instance
4. Review application logs: `docker logs fluxtrader-app`

**Production URL**: http://34.238.167.174:8000
**Health Check**: http://34.238.167.174:8000/health

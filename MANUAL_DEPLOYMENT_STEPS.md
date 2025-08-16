# Manual Deployment Steps for FluxTrader Backend

## 🚀 **Quick Deployment Guide**

Since SSH port 22 is open on your EC2 instance, here are the manual steps to get the backend running:

### **Step 1: Connect to EC2 Instance**

```bash
# Try connecting with different users (one of these should work):
ssh ec2-user@34.238.167.174
# OR
ssh ubuntu@34.238.167.174
# OR
ssh admin@34.238.167.174
```

### **Step 2: Install Docker (if not installed)**

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -a -G docker $USER

# Restart session or run:
newgrp docker
```

### **Step 3: Clone the Repository**

```bash
# Clone the FluxTrader repository
git clone https://github.com/Anki246/kamikaze-be.git

# Navigate to the project
cd kamikaze-be
```

### **Step 4: Build and Run with Docker**

```bash
# Build the Docker image
docker build -t fluxtrader:latest .

# Run the container
docker run -d \
    --name fluxtrader-app \
    --restart unless-stopped \
    -p 8000:8000 \
    -e ENVIRONMENT=production \
    -e USE_AWS_SECRETS=false \
    -e DB_HOST=localhost \
    -e DB_PORT=5432 \
    -e DB_NAME=kamikaze \
    -e DB_USER=postgres \
    -e DB_PASSWORD=admin2025 \
    fluxtrader:latest
```

### **Step 5: Verify Deployment**

```bash
# Check if container is running
docker ps

# Check container logs
docker logs fluxtrader-app

# Test the application
curl http://localhost:8000/health
```

---

## 🐍 **Alternative: Direct Python Deployment**

If Docker doesn't work, you can run the backend directly:

### **Step 1: Install Python and Dependencies**

```bash
# Install Python 3.11
sudo yum install -y python3 python3-pip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### **Step 2: Set Environment Variables**

```bash
export PYTHONPATH=/home/$USER/kamikaze-be/src
export PYTHONUNBUFFERED=1
export ENVIRONMENT=production
export USE_AWS_SECRETS=false
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=kamikaze
export DB_USER=postgres
export DB_PASSWORD=admin2025
```

### **Step 3: Start the Backend**

```bash
# Start the backend
python app.py --host 0.0.0.0 --port 8000

# OR run in background
nohup python app.py --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

---

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **Permission Denied (SSH)**
   ```bash
   # Try different users: ec2-user, ubuntu, admin
   # Check if you need to add your SSH key
   ```

2. **Docker Permission Denied**
   ```bash
   sudo usermod -a -G docker $USER
   newgrp docker
   ```

3. **Port 8000 Already in Use**
   ```bash
   # Kill existing processes
   sudo fuser -k 8000/tcp
   
   # OR use different port
   docker run -p 8080:8000 ...
   ```

4. **Container Won't Start**
   ```bash
   # Check logs
   docker logs fluxtrader-app
   
   # Remove and rebuild
   docker rm fluxtrader-app
   docker rmi fluxtrader:latest
   docker build -t fluxtrader:latest .
   ```

---

## ✅ **Verification Commands**

After deployment, run these to verify everything works:

```bash
# Check if application is running
curl http://34.238.167.174:8000/health

# Check API documentation
curl http://34.238.167.174:8000/docs

# Check container status
docker ps -f name=fluxtrader-app

# Check logs
docker logs fluxtrader-app

# Check port usage
sudo netstat -tlnp | grep :8000
```

---

## 🌐 **Expected URLs**

Once deployed, these URLs should work:

- **Health Check**: http://34.238.167.174:8000/health
- **API Documentation**: http://34.238.167.174:8000/docs
- **Root Endpoint**: http://34.238.167.174:8000/
- **API Info**: http://34.238.167.174:8000/api/info

---

## 🚨 **Security Note**

Since this is an open instance, make sure to:

1. **Secure the instance** after testing
2. **Use proper authentication** for production
3. **Configure security groups** appropriately
4. **Update passwords** and credentials

---

## 📞 **Need Help?**

If you encounter issues:

1. **Check container logs**: `docker logs fluxtrader-app`
2. **Verify port access**: `sudo netstat -tlnp | grep :8000`
3. **Test locally first**: `curl http://localhost:8000/health`
4. **Check security groups**: Ensure port 8000 is open in AWS

**Quick Test**: After deployment, run:
```bash
curl http://34.238.167.174:8000/health
```

This should return a JSON response with status information.

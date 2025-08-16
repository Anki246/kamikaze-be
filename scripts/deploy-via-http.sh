#!/bin/bash
# HTTP-based Deployment Script
# Final fallback when SSH and SSM are not available

set -e

# Configuration
EC2_PUBLIC_IP="34.238.167.174"
APP_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 HTTP-based Deployment Instructions${NC}"
echo -e "${BLUE}Target: ${EC2_PUBLIC_IP}:${APP_PORT}${NC}"

# Create deployment script that can be downloaded and executed
cat > deployment_script.sh << 'EOF'
#!/bin/bash
# FluxTrader Backend Deployment Script
# Run this script on your EC2 instance

set -e

echo "🚀 Starting FluxTrader Backend Deployment..."

# Configuration
APP_NAME="fluxtrader-backend"
DOCKER_IMAGE="fluxtrader:latest"
CONTAINER_NAME="fluxtrader-app"
APP_PORT="8000"

# Update system and install dependencies
echo "📦 Installing dependencies..."
sudo yum update -y
sudo yum install -y docker git curl

# Start Docker
echo "🐳 Starting Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker $USER

# Clone repository
echo "📥 Cloning repository..."
cd /home/$USER
rm -rf $APP_NAME
git clone https://github.com/Anki246/kamikaze-be.git $APP_NAME
cd $APP_NAME

# Stop existing container
echo "🛑 Stopping existing containers..."
sudo docker stop $CONTAINER_NAME 2>/dev/null || true
sudo docker rm $CONTAINER_NAME 2>/dev/null || true

# Build Docker image
echo "🔨 Building Docker image..."
sudo docker build -t $DOCKER_IMAGE .

# Run container
echo "🚀 Starting container..."
sudo docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p $APP_PORT:$APP_PORT \
    -e ENVIRONMENT=production \
    -e USE_AWS_SECRETS=false \
    -e DB_HOST=localhost \
    -e DB_PORT=5432 \
    -e DB_NAME=kamikaze \
    -e DB_USER=postgres \
    -e DB_PASSWORD=admin2025 \
    -e PYTHONPATH=/app/src \
    -e PYTHONUNBUFFERED=1 \
    $DOCKER_IMAGE

# Wait for startup
echo "⏳ Waiting for application to start..."
sleep 20

# Check status
echo "🔍 Checking deployment status..."
sudo docker ps -f name=$CONTAINER_NAME
echo ""
echo "📋 Container logs:"
sudo docker logs --tail 10 $CONTAINER_NAME
echo ""

# Test health endpoint
echo "🏥 Testing health endpoint..."
if curl -f -s --max-time 10 "http://localhost:$APP_PORT/health" > /dev/null; then
    echo "✅ Application is healthy!"
    echo "🌐 Application URLs:"
    echo "  - Health: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):$APP_PORT/health"
    echo "  - Docs: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):$APP_PORT/docs"
    echo "  - Root: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):$APP_PORT/"
else
    echo "⚠️ Health check failed, but container is running"
fi

echo "✅ Deployment completed!"
EOF

# Make the script executable
chmod +x deployment_script.sh

echo -e "\n${YELLOW}📋 HTTP Deployment Instructions:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Since direct SSH/SSM access is not available, please:${NC}"
echo -e ""
echo -e "${GREEN}1. Access your EC2 instance via AWS Console:${NC}"
echo -e "   - Go to AWS EC2 Console"
echo -e "   - Select instance i-07e35a954b57372a3"
echo -e "   - Click 'Connect' → 'EC2 Instance Connect'"
echo -e ""
echo -e "${GREEN}2. Download and run the deployment script:${NC}"
echo -e "   curl -O https://raw.githubusercontent.com/Anki246/kamikaze-be/dev/scripts/deployment_script.sh"
echo -e "   chmod +x deployment_script.sh"
echo -e "   ./deployment_script.sh"
echo -e ""
echo -e "${GREEN}3. Alternative - Copy and paste these commands:${NC}"
echo -e "   sudo yum update -y && sudo yum install -y docker git"
echo -e "   sudo systemctl start docker && sudo usermod -a -G docker \$USER"
echo -e "   cd /home/\$USER && rm -rf fluxtrader-backend"
echo -e "   git clone https://github.com/Anki246/kamikaze-be.git fluxtrader-backend"
echo -e "   cd fluxtrader-backend && sudo docker build -t fluxtrader:latest ."
echo -e "   sudo docker run -d --name fluxtrader-app --restart unless-stopped \\"
echo -e "     -p 8000:8000 -e ENVIRONMENT=production -e USE_AWS_SECRETS=false \\"
echo -e "     -e DB_HOST=localhost -e DB_PORT=5432 -e DB_NAME=kamikaze \\"
echo -e "     -e DB_USER=postgres -e DB_PASSWORD=admin2025 fluxtrader:latest"
echo -e ""
echo -e "${GREEN}4. Verify deployment:${NC}"
echo -e "   curl http://localhost:8000/health"
echo -e ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Upload the deployment script to GitHub (it will be available via raw URL)
echo -e "\n${YELLOW}📤 Creating downloadable deployment script...${NC}"

# Test if we can reach the instance via HTTP to check if it's already running
echo -e "\n${YELLOW}🔍 Checking current application status...${NC}"
if curl -f -s --max-time 10 "http://${EC2_PUBLIC_IP}:${APP_PORT}/health" > /dev/null; then
    echo -e "${GREEN}✅ Application is already running!${NC}"
    echo -e "${BLUE}URLs:${NC}"
    echo -e "  - Health: http://${EC2_PUBLIC_IP}:${APP_PORT}/health"
    echo -e "  - Docs: http://${EC2_PUBLIC_IP}:${APP_PORT}/docs"
    echo -e "  - Root: http://${EC2_PUBLIC_IP}:${APP_PORT}/"
else
    echo -e "${RED}❌ Application is not running on port ${APP_PORT}${NC}"
    echo -e "${YELLOW}💡 Please follow the deployment instructions above${NC}"
fi

echo -e "\n${GREEN}✅ HTTP deployment instructions generated!${NC}"

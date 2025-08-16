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

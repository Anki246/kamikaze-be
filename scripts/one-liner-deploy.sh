#!/bin/bash
# One-liner deployment script for FluxTrader Backend
# Copy and paste this entire script into your EC2 instance

echo "🚀 Starting FluxTrader Backend Deployment..."

# Update system and install Docker
sudo yum update -y
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker $USER

# Clone repository
cd /home/$USER
rm -rf kamikaze-be
git clone https://github.com/Anki246/kamikaze-be.git
cd kamikaze-be

# Stop any existing containers
docker stop fluxtrader-app 2>/dev/null || true
docker rm fluxtrader-app 2>/dev/null || true

# Build and run
docker build -t fluxtrader:latest .
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
    -e PYTHONPATH=/app/src \
    -e PYTHONUNBUFFERED=1 \
    fluxtrader:latest

# Wait and test
sleep 15
echo "🔍 Testing deployment..."
docker ps -f name=fluxtrader-app
echo "📋 Container logs:"
docker logs --tail 10 fluxtrader-app
echo "🏥 Health check:"
curl -s http://localhost:8000/health || echo "Health check failed"

echo "✅ Deployment completed!"
echo "🌐 URLs:"
echo "  - Health: http://34.238.167.174:8000/health"
echo "  - Docs: http://34.238.167.174:8000/docs"
echo "  - Root: http://34.238.167.174:8000/"

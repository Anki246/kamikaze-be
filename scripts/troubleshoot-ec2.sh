#!/bin/bash
# EC2 Troubleshooting Script for FluxTrader Backend

echo "🔍 FluxTrader Backend Troubleshooting"
echo "======================================"

# Check current user
echo "👤 Current user: $(whoami)"
echo "🏠 Home directory: $HOME"
echo "📍 Current directory: $(pwd)"

# Check OS
echo ""
echo "🖥️  Operating System:"
cat /etc/os-release | head -3

# Check Docker installation
echo ""
echo "🐳 Docker Status:"
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed"
    docker --version
    
    if sudo systemctl is-active --quiet docker; then
        echo "✅ Docker service is running"
    else
        echo "❌ Docker service is not running"
        echo "🔧 Starting Docker..."
        sudo systemctl start docker
    fi
    
    # Check Docker permissions
    if groups $USER | grep -q docker; then
        echo "✅ User is in docker group"
    else
        echo "❌ User not in docker group"
        echo "🔧 Adding user to docker group..."
        sudo usermod -a -G docker $USER
        echo "⚠️  Please logout and login again for group changes to take effect"
    fi
else
    echo "❌ Docker is not installed"
fi

# Check if FluxTrader container exists
echo ""
echo "📦 FluxTrader Container Status:"
if sudo docker ps -a | grep -q fluxtrader-app; then
    echo "✅ FluxTrader container exists"
    sudo docker ps -a -f name=fluxtrader-app
    
    if sudo docker ps | grep -q fluxtrader-app; then
        echo "✅ Container is running"
    else
        echo "❌ Container is not running"
        echo "📋 Container logs:"
        sudo docker logs --tail 20 fluxtrader-app
    fi
else
    echo "❌ FluxTrader container does not exist"
fi

# Check port 8000
echo ""
echo "🔌 Port 8000 Status:"
if sudo netstat -tlnp | grep -q :8000; then
    echo "✅ Port 8000 is in use"
    sudo netstat -tlnp | grep :8000
else
    echo "❌ Port 8000 is not in use"
fi

# Check if repository exists
echo ""
echo "📁 Repository Status:"
if [ -d "/home/$USER/fluxtrader-backend" ]; then
    echo "✅ Repository exists at /home/$USER/fluxtrader-backend"
    ls -la /home/$USER/fluxtrader-backend/
else
    echo "❌ Repository does not exist"
fi

# Test local connectivity
echo ""
echo "🌐 Local Connectivity Test:"
if curl -f -s --max-time 5 http://localhost:8000/health > /dev/null; then
    echo "✅ Application responds on localhost:8000"
    curl -s http://localhost:8000/health | head -3
else
    echo "❌ Application does not respond on localhost:8000"
fi

# Check public IP
echo ""
echo "🌍 Public IP Information:"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "Unable to get public IP")
echo "Public IP: $PUBLIC_IP"

# Test external connectivity
if [ "$PUBLIC_IP" != "Unable to get public IP" ]; then
    echo "🔗 External Connectivity Test:"
    if curl -f -s --max-time 5 http://$PUBLIC_IP:8000/health > /dev/null; then
        echo "✅ Application responds on $PUBLIC_IP:8000"
    else
        echo "❌ Application does not respond on $PUBLIC_IP:8000"
        echo "💡 This might be a security group issue"
    fi
fi

# Check security group recommendations
echo ""
echo "🛡️  Security Group Requirements:"
echo "Make sure your EC2 security group allows:"
echo "  - Inbound: Port 8000 from 0.0.0.0/0 (Custom TCP)"
echo "  - Inbound: Port 22 from your IP (SSH)"
echo "  - Outbound: All traffic (default)"

# Provide next steps
echo ""
echo "🔧 Troubleshooting Steps:"
echo "1. If Docker not installed: Run deployment script"
echo "2. If container not running: Check logs above"
echo "3. If port not accessible externally: Check security groups"
echo "4. If application not responding: Restart container"

echo ""
echo "🚀 Quick Fix Commands:"
echo "# Restart container:"
echo "sudo docker restart fluxtrader-app"
echo ""
echo "# Rebuild and restart:"
echo "cd /home/$USER/fluxtrader-backend"
echo "sudo docker stop fluxtrader-app && sudo docker rm fluxtrader-app"
echo "sudo docker build -t fluxtrader:latest ."
echo "sudo docker run -d --name fluxtrader-app --restart unless-stopped -p 8000:8000 -e ENVIRONMENT=production fluxtrader:latest"
echo ""
echo "# Check logs:"
echo "sudo docker logs -f fluxtrader-app"

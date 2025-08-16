#!/bin/bash
# FluxTrader Staging Environment Setup Script
# This script configures an EC2 instance for the FluxTrader staging environment

set -e

# Logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting FluxTrader staging environment setup..."

# Update system
echo "📦 Updating system packages..."
yum update -y

# Install Docker
echo "🐳 Installing Docker..."
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Install AWS CLI v2
echo "☁️ Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install CloudWatch agent
echo "📊 Installing CloudWatch agent..."
yum install -y amazon-cloudwatch-agent

# Install additional tools
echo "🛠️ Installing additional tools..."
yum install -y htop curl wget git jq

# Create application directories
echo "📁 Creating application directories..."
mkdir -p /opt/fluxtrader/{logs,data,config,backups}
mkdir -p /opt/fluxtrader/logs/{system,trading_sessions,archived}
chown -R ec2-user:ec2-user /opt/fluxtrader

# Set up environment variables
echo "🔧 Setting up environment variables..."
cat > /etc/environment << EOF
ENVIRONMENT=staging
AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
EOF

# Create systemd service for FluxTrader
echo "⚙️ Creating FluxTrader systemd service..."
cat > /etc/systemd/system/fluxtrader.service << 'EOF'
[Unit]
Description=FluxTrader Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'docker run -d --name fluxtrader-staging --restart unless-stopped -p 8000:8000 -e ENVIRONMENT=staging -e AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region) -v /opt/fluxtrader/logs:/app/logs ghcr.io/your-username/kamikaze-be/fluxtrader:staging-latest'
ExecStop=/usr/bin/docker stop fluxtrader-staging
ExecStopPost=/usr/bin/docker rm fluxtrader-staging
User=ec2-user
Group=docker

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (but don't start it yet - will be started by deployment)
systemctl daemon-reload
systemctl enable fluxtrader.service

# Configure CloudWatch agent
echo "📊 Configuring CloudWatch agent..."
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/opt/fluxtrader/logs/system/*.log",
                        "log_group_name": "/fluxtrader/staging/system",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/opt/fluxtrader/logs/trading_sessions/*.log",
                        "log_group_name": "/fluxtrader/staging/trading",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/fluxtrader/staging/user-data",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "FluxTrader/Staging",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 60
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Set up log rotation
echo "📋 Setting up log rotation..."
cat > /etc/logrotate.d/fluxtrader << EOF
/opt/fluxtrader/logs/system/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
    postrotate
        /bin/systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}

/opt/fluxtrader/logs/trading_sessions/*.log {
    daily
    missingok
    rotate 90
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
}
EOF

# Create health check script
echo "🔍 Creating health check script..."
cat > /opt/fluxtrader/health-check.sh << 'EOF'
#!/bin/bash
# FluxTrader Health Check Script

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/opt/fluxtrader/logs/system/health-check.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check if container is running
if ! docker ps | grep -q fluxtrader-staging; then
    log "ERROR: FluxTrader container is not running"
    exit 1
fi

# Check application health endpoint
if curl -f "$HEALTH_URL" --connect-timeout 5 --max-time 10 > /dev/null 2>&1; then
    log "INFO: Health check passed"
    exit 0
else
    log "ERROR: Health check failed"
    exit 1
fi
EOF

chmod +x /opt/fluxtrader/health-check.sh

# Set up cron job for health checks
echo "⏰ Setting up health check cron job..."
echo "*/5 * * * * ec2-user /opt/fluxtrader/health-check.sh" >> /etc/crontab

# Create backup script
echo "💾 Creating backup script..."
cat > /opt/fluxtrader/backup.sh << 'EOF'
#!/bin/bash
# FluxTrader Backup Script

BACKUP_DIR="/opt/fluxtrader/backups"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/fluxtrader/logs/system/backup.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "INFO: Starting backup process"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" -C /opt/fluxtrader logs/
log "INFO: Logs backed up to logs_$DATE.tar.gz"

# Backup configuration (if any)
if [ -d "/opt/fluxtrader/config" ]; then
    tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C /opt/fluxtrader config/
    log "INFO: Configuration backed up to config_$DATE.tar.gz"
fi

# Clean up old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
log "INFO: Old backups cleaned up"

log "INFO: Backup process completed"
EOF

chmod +x /opt/fluxtrader/backup.sh

# Set up daily backup cron job
echo "0 2 * * * ec2-user /opt/fluxtrader/backup.sh" >> /etc/crontab

# Configure firewall (if needed)
echo "🔥 Configuring firewall..."
# Amazon Linux 2023 uses firewalld by default
systemctl start firewalld
systemctl enable firewalld
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload

# Set up monitoring alerts (placeholder)
echo "📢 Setting up monitoring alerts..."
# This would integrate with SNS, CloudWatch Alarms, etc.

# Final setup
echo "🎯 Final setup steps..."
chown -R ec2-user:ec2-user /opt/fluxtrader
chmod -R 755 /opt/fluxtrader

# Signal completion
echo "✅ FluxTrader staging environment setup completed successfully!"
echo "📋 Instance is ready for deployment"
echo "🔍 Health check endpoint: http://localhost:8000/health"
echo "📊 Logs location: /opt/fluxtrader/logs/"
echo "💾 Backups location: /opt/fluxtrader/backups/"

# Create completion marker
touch /opt/fluxtrader/.setup-complete
echo "$(date)" > /opt/fluxtrader/.setup-complete

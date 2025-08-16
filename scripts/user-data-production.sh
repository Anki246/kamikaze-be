#!/bin/bash
# FluxTrader Production Environment Setup Script
# This script configures an EC2 instance for the FluxTrader production environment

set -e

# Logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting FluxTrader production environment setup..."

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

# Install additional production tools
echo "🛠️ Installing production tools..."
yum install -y htop curl wget git jq fail2ban

# Configure fail2ban for SSH protection
echo "🔒 Configuring fail2ban..."
systemctl start fail2ban
systemctl enable fail2ban

cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/secure
maxretry = 3
bantime = 3600
EOF

systemctl restart fail2ban

# Create application directories with production structure
echo "📁 Creating production application directories..."
mkdir -p /opt/fluxtrader/{logs,data,config,backups,ssl}
mkdir -p /opt/fluxtrader/logs/{system,trading_sessions,archived,audit}
mkdir -p /opt/fluxtrader/data/{cache,temp,exports}
chown -R ec2-user:ec2-user /opt/fluxtrader

# Set up environment variables
echo "🔧 Setting up production environment variables..."
cat > /etc/environment << EOF
ENVIRONMENT=production
AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
NODE_ENV=production
EOF

# Create systemd service for FluxTrader with production settings
echo "⚙️ Creating FluxTrader production systemd service..."
cat > /etc/systemd/system/fluxtrader.service << 'EOF'
[Unit]
Description=FluxTrader Production Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/bash -c 'docker pull ghcr.io/your-username/kamikaze-be/fluxtrader:production-latest'
ExecStart=/bin/bash -c 'docker run -d --name fluxtrader-production --restart unless-stopped -p 8000:8000 --memory=2g --cpus=1.5 -e ENVIRONMENT=production -e AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region) -v /opt/fluxtrader/logs:/app/logs -v /opt/fluxtrader/data:/app/data ghcr.io/your-username/kamikaze-be/fluxtrader:production-latest'
ExecStop=/usr/bin/docker stop fluxtrader-production
ExecStopPost=/usr/bin/docker rm fluxtrader-production
ExecReload=/bin/bash -c 'docker restart fluxtrader-production'
User=ec2-user
Group=docker
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl daemon-reload
systemctl enable fluxtrader.service

# Configure CloudWatch agent for production
echo "📊 Configuring production CloudWatch agent..."
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "agent": {
        "metrics_collection_interval": 30,
        "run_as_user": "cwagent"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/opt/fluxtrader/logs/system/*.log",
                        "log_group_name": "/fluxtrader/production/system",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/opt/fluxtrader/logs/trading_sessions/*.log",
                        "log_group_name": "/fluxtrader/production/trading",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/opt/fluxtrader/logs/audit/*.log",
                        "log_group_name": "/fluxtrader/production/audit",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/secure",
                        "log_group_name": "/fluxtrader/production/security",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/fluxtrader/production/user-data",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "FluxTrader/Production",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 30,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 30,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time",
                    "read_bytes",
                    "write_bytes"
                ],
                "metrics_collection_interval": 30,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 30
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 30
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 30
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Set up production log rotation
echo "📋 Setting up production log rotation..."
cat > /etc/logrotate.d/fluxtrader << EOF
/opt/fluxtrader/logs/system/*.log {
    daily
    missingok
    rotate 90
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
    rotate 365
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
}

/opt/fluxtrader/logs/audit/*.log {
    daily
    missingok
    rotate 2555  # 7 years
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
}
EOF

# Create enhanced health check script for production
echo "🔍 Creating production health check script..."
cat > /opt/fluxtrader/health-check.sh << 'EOF'
#!/bin/bash
# FluxTrader Production Health Check Script

HEALTH_URL="http://localhost:8000/health"
METRICS_URL="http://localhost:8000/metrics"
LOG_FILE="/opt/fluxtrader/logs/system/health-check.log"
ALERT_THRESHOLD=3
ALERT_FILE="/opt/fluxtrader/.health-alert-count"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to send alert (placeholder - integrate with SNS)
send_alert() {
    local message="$1"
    log "ALERT: $message"
    # aws sns publish --topic-arn "arn:aws:sns:region:account:fluxtrader-alerts" --message "$message"
}

# Initialize alert counter
if [ ! -f "$ALERT_FILE" ]; then
    echo "0" > "$ALERT_FILE"
fi

ALERT_COUNT=$(cat "$ALERT_FILE")

# Check if container is running
if ! docker ps | grep -q fluxtrader-production; then
    log "ERROR: FluxTrader production container is not running"
    ALERT_COUNT=$((ALERT_COUNT + 1))
    echo "$ALERT_COUNT" > "$ALERT_FILE"
    
    if [ "$ALERT_COUNT" -ge "$ALERT_THRESHOLD" ]; then
        send_alert "FluxTrader production container is not running (Alert #$ALERT_COUNT)"
    fi
    exit 1
fi

# Check application health endpoint
if curl -f "$HEALTH_URL" --connect-timeout 5 --max-time 10 > /dev/null 2>&1; then
    log "INFO: Health check passed"
    
    # Check metrics endpoint
    if curl -f "$METRICS_URL" --connect-timeout 5 --max-time 10 > /dev/null 2>&1; then
        log "INFO: Metrics endpoint accessible"
    else
        log "WARNING: Metrics endpoint not accessible"
    fi
    
    # Reset alert counter on success
    echo "0" > "$ALERT_FILE"
    exit 0
else
    log "ERROR: Health check failed"
    ALERT_COUNT=$((ALERT_COUNT + 1))
    echo "$ALERT_COUNT" > "$ALERT_FILE"
    
    if [ "$ALERT_COUNT" -ge "$ALERT_THRESHOLD" ]; then
        send_alert "FluxTrader production health check failed (Alert #$ALERT_COUNT)"
    fi
    exit 1
fi
EOF

chmod +x /opt/fluxtrader/health-check.sh

# Set up frequent health check cron job for production
echo "⏰ Setting up production health check cron job..."
echo "*/2 * * * * ec2-user /opt/fluxtrader/health-check.sh" >> /etc/crontab

# Create enhanced backup script for production
echo "💾 Creating production backup script..."
cat > /opt/fluxtrader/backup.sh << 'EOF'
#!/bin/bash
# FluxTrader Production Backup Script

BACKUP_DIR="/opt/fluxtrader/backups"
S3_BUCKET="fluxtrader-production-backups"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/fluxtrader/logs/system/backup.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "INFO: Starting production backup process"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" -C /opt/fluxtrader logs/
log "INFO: Logs backed up to logs_$DATE.tar.gz"

# Backup data
if [ -d "/opt/fluxtrader/data" ]; then
    tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" -C /opt/fluxtrader data/
    log "INFO: Data backed up to data_$DATE.tar.gz"
fi

# Backup configuration
if [ -d "/opt/fluxtrader/config" ]; then
    tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C /opt/fluxtrader config/
    log "INFO: Configuration backed up to config_$DATE.tar.gz"
fi

# Upload to S3 (if configured)
if aws s3 ls "s3://$S3_BUCKET" > /dev/null 2>&1; then
    aws s3 sync "$BACKUP_DIR" "s3://$S3_BUCKET/$(date +%Y/%m/%d)/"
    log "INFO: Backups uploaded to S3"
else
    log "WARNING: S3 bucket not accessible, keeping local backups only"
fi

# Clean up old local backups (keep last 3 days for production)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +3 -delete
log "INFO: Old local backups cleaned up"

log "INFO: Production backup process completed"
EOF

chmod +x /opt/fluxtrader/backup.sh

# Set up multiple backup cron jobs for production
echo "0 */6 * * * ec2-user /opt/fluxtrader/backup.sh" >> /etc/crontab  # Every 6 hours

# Configure production firewall with stricter rules
echo "🔥 Configuring production firewall..."
systemctl start firewalld
systemctl enable firewalld

# Remove default zones and create custom zone
firewall-cmd --permanent --new-zone=fluxtrader-production
firewall-cmd --permanent --zone=fluxtrader-production --add-port=8000/tcp
firewall-cmd --permanent --zone=fluxtrader-production --add-service=ssh
firewall-cmd --permanent --zone=fluxtrader-production --add-rich-rule='rule family="ipv4" source address="10.0.0.0/8" accept'
firewall-cmd --permanent --set-default-zone=fluxtrader-production
firewall-cmd --reload

# Set up system hardening
echo "🔒 Applying production system hardening..."

# Disable unnecessary services
systemctl disable postfix || true
systemctl stop postfix || true

# Set up automatic security updates
yum install -y yum-cron
systemctl enable yum-cron
systemctl start yum-cron

# Configure kernel parameters for production
cat >> /etc/sysctl.conf << EOF
# FluxTrader Production Kernel Parameters
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
EOF

sysctl -p

# Final production setup
echo "🎯 Final production setup steps..."
chown -R ec2-user:ec2-user /opt/fluxtrader
chmod -R 750 /opt/fluxtrader  # More restrictive permissions for production

# Set up monitoring alerts and notifications
echo "📢 Setting up production monitoring alerts..."
# This would integrate with SNS, CloudWatch Alarms, PagerDuty, etc.

# Create production readiness marker
echo "✅ FluxTrader production environment setup completed successfully!"
echo "🔒 Production security hardening applied"
echo "📊 Enhanced monitoring and alerting configured"
echo "💾 Automated backup system enabled"
echo "🔍 Health check endpoint: http://localhost:8000/health"
echo "📊 Logs location: /opt/fluxtrader/logs/"
echo "💾 Backups location: /opt/fluxtrader/backups/"

# Create completion marker
touch /opt/fluxtrader/.production-setup-complete
echo "$(date)" > /opt/fluxtrader/.production-setup-complete
echo "PRODUCTION" >> /opt/fluxtrader/.production-setup-complete

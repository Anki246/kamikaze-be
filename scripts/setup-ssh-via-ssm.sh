#!/bin/bash
# Setup SSH access on EC2 instance that was launched without key pair
# Uses AWS Systems Manager to add SSH public key to authorized_keys

set -e

# Configuration
EC2_INSTANCE_ID="i-07e35a954b57372a3"
EC2_PUBLIC_IP="34.238.167.174"
SSH_PUBLIC_KEY_PATH="~/.ssh/kmkz-key-ec2.pub"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up SSH access via AWS Systems Manager${NC}"
echo -e "${BLUE}Instance: ${EC2_INSTANCE_ID} (${EC2_PUBLIC_IP})${NC}"

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found${NC}"
    echo -e "${YELLOW}💡 Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html${NC}"
    exit 1
fi

# Check if SSH public key exists
if [ ! -f ~/.ssh/kmkz-key-ec2.pub ]; then
    echo -e "${YELLOW}🔑 SSH public key not found, generating from private key...${NC}"
    if [ -f ~/.ssh/kmkz-key-ec2.pem ]; then
        ssh-keygen -y -f ~/.ssh/kmkz-key-ec2.pem > ~/.ssh/kmkz-key-ec2.pub
        echo -e "${GREEN}✅ Generated public key from private key${NC}"
    else
        echo -e "${RED}❌ No SSH keys found${NC}"
        exit 1
    fi
fi

# Read the public key
PUBLIC_KEY=$(cat ~/.ssh/kmkz-key-ec2.pub)
echo -e "${BLUE}📋 Public key: ${PUBLIC_KEY}${NC}"

# Test SSM connectivity
echo -e "${YELLOW}🔍 Testing SSM connectivity...${NC}"
if aws ssm describe-instance-information --filters "Key=InstanceIds,Values=${EC2_INSTANCE_ID}" --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null | grep -q "Online"; then
    echo -e "${GREEN}✅ SSM connectivity confirmed${NC}"
else
    echo -e "${RED}❌ SSM connectivity failed${NC}"
    echo -e "${YELLOW}💡 Ensure the EC2 instance has SSM agent installed and proper IAM role${NC}"
    exit 1
fi

# Add SSH public key to authorized_keys via SSM
echo -e "${YELLOW}🔑 Adding SSH public key to EC2 instance...${NC}"

# Create the command to add SSH key
SSM_COMMAND="
# Create .ssh directory if it doesn't exist
mkdir -p /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh

# Add public key to authorized_keys
echo '${PUBLIC_KEY}' >> /home/ubuntu/.ssh/authorized_keys
chmod 600 /home/ubuntu/.ssh/authorized_keys
chown -R ubuntu:ubuntu /home/ubuntu/.ssh

# Also add for ec2-user (in case it's Amazon Linux)
mkdir -p /home/ec2-user/.ssh
chmod 700 /home/ec2-user/.ssh
echo '${PUBLIC_KEY}' >> /home/ec2-user/.ssh/authorized_keys
chmod 600 /home/ec2-user/.ssh/authorized_keys
chown -R ec2-user:ec2-user /home/ec2-user/.ssh

echo 'SSH key added successfully'
"

# Execute the command via SSM
COMMAND_ID=$(aws ssm send-command \
    --instance-ids ${EC2_INSTANCE_ID} \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[\"${SSM_COMMAND}\"]" \
    --query 'Command.CommandId' \
    --output text)

echo -e "${BLUE}📤 SSM Command ID: ${COMMAND_ID}${NC}"

# Wait for command to complete
echo -e "${YELLOW}⏳ Waiting for command to complete...${NC}"
sleep 10

# Check command status
STATUS=$(aws ssm get-command-invocation \
    --command-id ${COMMAND_ID} \
    --instance-id ${EC2_INSTANCE_ID} \
    --query 'Status' \
    --output text)

echo -e "${BLUE}📋 Command Status: ${STATUS}${NC}"

if [ "$STATUS" = "Success" ]; then
    echo -e "${GREEN}✅ SSH key added successfully${NC}"
    
    # Test SSH connection
    echo -e "${YELLOW}🔍 Testing SSH connection...${NC}"
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/kmkz-key-ec2.pem ubuntu@${EC2_PUBLIC_IP} "echo 'SSH connection successful'"; then
        echo -e "${GREEN}✅ SSH connection successful with ubuntu user${NC}"
    elif ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/kmkz-key-ec2.pem ec2-user@${EC2_PUBLIC_IP} "echo 'SSH connection successful'"; then
        echo -e "${GREEN}✅ SSH connection successful with ec2-user${NC}"
    else
        echo -e "${RED}❌ SSH connection still failing${NC}"
        echo -e "${YELLOW}📋 Command output:${NC}"
        aws ssm get-command-invocation \
            --command-id ${COMMAND_ID} \
            --instance-id ${EC2_INSTANCE_ID} \
            --query 'StandardOutputContent' \
            --output text
    fi
else
    echo -e "${RED}❌ Command failed with status: ${STATUS}${NC}"
    echo -e "${YELLOW}📋 Error output:${NC}"
    aws ssm get-command-invocation \
        --command-id ${COMMAND_ID} \
        --instance-id ${EC2_INSTANCE_ID} \
        --query 'StandardErrorContent' \
        --output text
fi

echo -e "${BLUE}🏁 SSH setup completed${NC}"

#!/bin/bash
# Kamikaze-be Infrastructure-as-Code Deployment Script
# Deploys infrastructure using Terraform and application using Docker

set -e

# Configuration
PROJECT_NAME="kamikaze-be"
TERRAFORM_DIR="infrastructure/terraform"
DOCKER_IMAGE="${PROJECT_NAME}:latest"
CONTAINER_NAME="${PROJECT_NAME}-app"
APP_PORT="8000"
SECRETS_NAME="kmkz-secrets"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Infrastructure-as-Code Deployment${NC}"
echo -e "${BLUE}Project: ${PROJECT_NAME}${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT:-development}${NC}"

# Function to check required environment variables
check_environment() {
    echo -e "${YELLOW}🔍 Checking environment variables...${NC}"
    
    local required_vars=(
        "AWS_ACCESS_KEY_ID"
        "AWS_SECRET_ACCESS_KEY" 
        "AWS_DEFAULT_REGION"
        "DB_PASSWORD"
        "EC2_PUBLIC_KEY"
        "ENVIRONMENT"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        else
            echo -e "${GREEN}✅ $var is set${NC}"
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '%s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All required environment variables are set${NC}"
}

# Function to initialize Terraform
init_terraform() {
    echo -e "${YELLOW}🏗️ Initializing Terraform...${NC}"
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    terraform init
    
    # Validate configuration
    terraform validate
    
    echo -e "${GREEN}✅ Terraform initialized successfully${NC}"
    cd - > /dev/null
}

# Function to plan infrastructure
plan_infrastructure() {
    echo -e "${YELLOW}📋 Planning infrastructure changes...${NC}"
    
    cd "$TERRAFORM_DIR"
    
    # Create terraform.tfvars from environment variables
    cat > terraform.tfvars << EOF
aws_region = "${AWS_DEFAULT_REGION}"
project_name = "${PROJECT_NAME}"
environment = "${ENVIRONMENT}"
ec2_public_key = "${EC2_PUBLIC_KEY}"
db_password = "${DB_PASSWORD}"
app_port = ${APP_PORT}
secrets_manager_name = "${SECRETS_NAME}"
EOF
    
    # Plan infrastructure
    terraform plan -out=tfplan
    
    echo -e "${GREEN}✅ Infrastructure plan created${NC}"
    cd - > /dev/null
}

# Function to apply infrastructure
apply_infrastructure() {
    echo -e "${YELLOW}🏗️ Applying infrastructure changes...${NC}"
    
    cd "$TERRAFORM_DIR"
    
    # Apply infrastructure
    terraform apply tfplan
    
    # Get outputs
    EC2_PUBLIC_IP=$(terraform output -raw ec2_public_ip)
    RDS_ENDPOINT=$(terraform output -raw database_endpoint)
    SECRETS_ARN=$(terraform output -raw secrets_manager_arn)
    
    echo -e "${GREEN}✅ Infrastructure applied successfully${NC}"
    echo -e "${BLUE}📊 Infrastructure Details:${NC}"
    echo -e "${BLUE}  EC2 Public IP: ${EC2_PUBLIC_IP}${NC}"
    echo -e "${BLUE}  RDS Endpoint: ${RDS_ENDPOINT}${NC}"
    echo -e "${BLUE}  Secrets ARN: ${SECRETS_ARN}${NC}"
    
    cd - > /dev/null
}

# Function to build Docker image
build_docker_image() {
    echo -e "${YELLOW}🐳 Building Docker image...${NC}"
    
    # Build Docker image
    docker build -t "$DOCKER_IMAGE" .
    
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
}

# Function to deploy application
deploy_application() {
    echo -e "${YELLOW}🚀 Deploying application to EC2...${NC}"
    
    # Get EC2 public IP from Terraform output
    cd "$TERRAFORM_DIR"
    EC2_PUBLIC_IP=$(terraform output -raw ec2_public_ip)
    cd - > /dev/null
    
    # Create deployment script
    cat > deploy_app.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
DOCKER_IMAGE="kamikaze-be:latest"
CONTAINER_NAME="kamikaze-app"
APP_PORT="8000"
SECRETS_NAME="kmkz-secrets"

echo "🐳 Installing Docker if not present..."
if ! command -v docker &> /dev/null; then
    sudo apt update -y
    sudo apt install -y docker.io awscli
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker ubuntu
    # Re-login to apply group changes
    newgrp docker
fi

echo "🛑 Stopping existing containers..."
sudo docker stop $CONTAINER_NAME 2>/dev/null || true
sudo docker rm $CONTAINER_NAME 2>/dev/null || true

echo "🗑️ Cleaning up old images..."
sudo docker image prune -f

echo "📥 Pulling latest Docker image..."
# In production, this would pull from a registry
# For now, we'll build locally or use the uploaded image

echo "🚀 Starting new container with AWS Secrets Manager..."
sudo docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p $APP_PORT:$APP_PORT \
    -e ENVIRONMENT=production \
    -e USE_AWS_SECRETS=true \
    -e AWS_SECRETS_NAME=$SECRETS_NAME \
    -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION \
    $DOCKER_IMAGE

echo "⏳ Waiting for application to start..."
sleep 30

echo "🏥 Checking application health..."
for i in {1..10}; do
    if curl -f http://localhost:$APP_PORT/health > /dev/null 2>&1; then
        echo "✅ Application is healthy"
        break
    else
        echo "⏳ Waiting for application... ($i/10)"
        sleep 10
    fi
    
    if [ $i -eq 10 ]; then
        echo "❌ Application health check failed"
        sudo docker logs $CONTAINER_NAME --tail 20
        exit 1
    fi
done

echo "✅ Application deployed successfully"
EOF

    # Make script executable
    chmod +x deploy_app.sh
    
    # Copy and execute deployment script on EC2
    echo -e "${BLUE}📤 Copying deployment script to EC2...${NC}"
    scp -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa deploy_app.sh ubuntu@$EC2_PUBLIC_IP:~/
    
    echo -e "${BLUE}🎯 Executing deployment on EC2...${NC}"
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa ubuntu@$EC2_PUBLIC_IP "
        export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION
        chmod +x deploy_app.sh
        ./deploy_app.sh
    "
    
    # Clean up local script
    rm deploy_app.sh
    
    echo -e "${GREEN}✅ Application deployed successfully${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
    
    cd "$TERRAFORM_DIR"
    EC2_PUBLIC_IP=$(terraform output -raw ec2_public_ip)
    cd - > /dev/null
    
    # Test application endpoints
    echo -e "${BLUE}🌐 Testing application endpoints...${NC}"
    
    # Health check
    if curl -f "http://$EC2_PUBLIC_IP:$APP_PORT/health" --connect-timeout 10; then
        echo -e "${GREEN}✅ Health endpoint working${NC}"
    else
        echo -e "${RED}❌ Health endpoint failed${NC}"
        return 1
    fi
    
    # Root endpoint
    if curl -f "http://$EC2_PUBLIC_IP:$APP_PORT/" --connect-timeout 10 > /dev/null; then
        echo -e "${GREEN}✅ Root endpoint working${NC}"
    else
        echo -e "${RED}❌ Root endpoint failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Deployment verification successful${NC}"
    echo -e "${BLUE}🎉 Application is available at: http://$EC2_PUBLIC_IP:$APP_PORT${NC}"
}

# Function to show deployment summary
show_summary() {
    echo -e "${BLUE}📋 Deployment Summary${NC}"
    echo -e "${BLUE}===================${NC}"
    
    cd "$TERRAFORM_DIR"
    echo -e "${GREEN}🏗️ Infrastructure:${NC}"
    echo -e "  EC2 Instance: $(terraform output -raw ec2_instance_id)"
    echo -e "  Public IP: $(terraform output -raw ec2_public_ip)"
    echo -e "  RDS Endpoint: $(terraform output -raw database_endpoint)"
    echo -e "  Secrets Manager: $(terraform output -raw secrets_manager_arn)"
    
    echo -e "${GREEN}🚀 Application:${NC}"
    echo -e "  URL: http://$(terraform output -raw ec2_public_ip):$APP_PORT"
    echo -e "  Health: http://$(terraform output -raw ec2_public_ip):$APP_PORT/health"
    echo -e "  API Docs: http://$(terraform output -raw ec2_public_ip):$APP_PORT/docs"
    
    cd - > /dev/null
}

# Main execution
main() {
    check_environment
    init_terraform
    plan_infrastructure
    apply_infrastructure
    build_docker_image
    deploy_application
    verify_deployment
    show_summary
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
}

# Execute main function
main "$@"

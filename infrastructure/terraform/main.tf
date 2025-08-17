# Kamikaze-be Infrastructure - Complete Terraform Configuration
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "environment" {
  description = "Environment name (staging or production)"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "key_pair_name" {
  description = "EC2 Key Pair name for SSH access"
  type        = string
}

variable "db_master_password" {
  description = "Master password for RDS instance"
  type        = string
  sensitive   = true
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access the application"
  type        = string
  default     = "0.0.0.0/0"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Local values
locals {
  common_tags = {
    Environment = var.environment
    Application = "fluxtrader"
    ManagedBy   = "terraform"
  }
  
  is_production = var.environment == "production"
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group
resource "aws_security_group" "fluxtrader" {
  name_prefix = "fluxtrader-${var.environment}-"
  description = "Security group for FluxTrader ${var.environment} environment"
  vpc_id      = data.aws_vpc.default.id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
    description = "SSH access"
  }

  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  # HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  # Application port (internal)
  ingress {
    from_port = 8000
    to_port   = 8000
    protocol  = "tcp"
    self      = true
    description = "Application port (internal)"
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "fluxtrader-${var.environment}-sg"
  })
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "fluxtrader_ec2" {
  name = "fluxtrader-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Secrets Manager Access
resource "aws_iam_policy" "secrets_manager_access" {
  name        = "fluxtrader-${var.environment}-secrets-manager-access"
  description = "Policy for FluxTrader to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:fluxtrader/${var.environment}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })

  tags = local.common_tags
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.fluxtrader_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "secrets_manager_access" {
  role       = aws_iam_role.fluxtrader_ec2.name
  policy_arn = aws_iam_policy.secrets_manager_access.arn
}

# Instance Profile
resource "aws_iam_instance_profile" "fluxtrader" {
  name = "fluxtrader-${var.environment}-instance-profile"
  role = aws_iam_role.fluxtrader_ec2.name

  tags = local.common_tags
}

# RDS Subnet Group
resource "aws_db_subnet_group" "fluxtrader" {
  name       = "fluxtrader-${var.environment}-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name = "fluxtrader-${var.environment}-db-subnet-group"
  })
}

# RDS Instance
resource "aws_db_instance" "fluxtrader" {
  identifier = "fluxtrader-${var.environment}"

  # Engine configuration
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.rds_instance_class

  # Database configuration
  db_name  = "kamikaze"
  username = "fluxtrader"
  password = var.db_master_password

  # Storage configuration
  allocated_storage     = local.is_production ? 100 : 20
  max_allocated_storage = local.is_production ? 1000 : 100
  storage_type          = "gp3"
  storage_encrypted     = true

  # High availability and backup
  multi_az               = local.is_production
  backup_retention_period = local.is_production ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  delete_automated_backups = !local.is_production
  deletion_protection    = local.is_production

  # Networking and security
  vpc_security_group_ids = [aws_security_group.fluxtrader.id]
  db_subnet_group_name   = aws_db_subnet_group.fluxtrader.name
  publicly_accessible    = false

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled    = local.is_production
  monitoring_interval             = local.is_production ? 60 : 0

  # Prevent accidental deletion
  skip_final_snapshot = !local.is_production
  final_snapshot_identifier = local.is_production ? "fluxtrader-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  tags = merge(local.common_tags, {
    Name = "fluxtrader-${var.environment}-db"
  })
}

# Launch Template
resource "aws_launch_template" "fluxtrader" {
  name_prefix   = "fluxtrader-${var.environment}-"
  image_id      = "ami-0c02fb55956c7d316"  # Amazon Linux 2023
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.fluxtrader.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.fluxtrader.name
  }

  user_data = base64encode(templatefile("${path.module}/../../scripts/user-data-${var.environment}.sh", {
    environment = var.environment
    aws_region  = var.aws_region
  }))

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "fluxtrader-${var.environment}"
    })
  }

  tags = local.common_tags
}

# EC2 Instance
resource "aws_instance" "fluxtrader" {
  launch_template {
    id      = aws_launch_template.fluxtrader.id
    version = "$Latest"
  }

  tags = merge(local.common_tags, {
    Name = "fluxtrader-${var.environment}"
  })
}

# Application Load Balancer (Production only)
resource "aws_lb" "fluxtrader" {
  count              = local.is_production ? 1 : 0
  name               = "fluxtrader-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.fluxtrader.id]
  subnets            = data.aws_subnets.default.ids

  enable_deletion_protection = local.is_production

  tags = merge(local.common_tags, {
    Name = "fluxtrader-${var.environment}-alb"
  })
}

# Target Group (Production only)
resource "aws_lb_target_group" "fluxtrader" {
  count    = local.is_production ? 1 : 0
  name     = "fluxtrader-${var.environment}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = merge(local.common_tags, {
    Name = "fluxtrader-${var.environment}-tg"
  })
}

# Target Group Attachment (Production only)
resource "aws_lb_target_group_attachment" "fluxtrader" {
  count            = local.is_production ? 1 : 0
  target_group_arn = aws_lb_target_group.fluxtrader[0].arn
  target_id        = aws_instance.fluxtrader.id
  port             = 8000
}

# ALB Listener (Production only)
resource "aws_lb_listener" "fluxtrader" {
  count             = local.is_production ? 1 : 0
  load_balancer_arn = aws_lb.fluxtrader[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.fluxtrader[0].arn
  }

  tags = local.common_tags
}

# Outputs
output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.fluxtrader.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.fluxtrader.public_ip
}

output "database_endpoint" {
  description = "RDS Database Endpoint"
  value       = aws_db_instance.fluxtrader.endpoint
}

output "database_port" {
  description = "RDS Database Port"
  value       = aws_db_instance.fluxtrader.port
}

output "load_balancer_dns" {
  description = "Application Load Balancer DNS Name"
  value       = local.is_production ? aws_lb.fluxtrader[0].dns_name : null
}

output "security_group_id" {
  description = "Security Group ID"
  value       = aws_security_group.fluxtrader.id
}

# AWS Secrets Manager
resource "aws_secretsmanager_secret" "app_secrets" {
  name        = var.secrets_manager_name
  description = "Application secrets for ${var.project_name}"

  tags = merge(var.common_tags, {
    Name        = var.secrets_manager_name
    Environment = var.environment
  })
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    database = {
      host     = aws_db_instance.fluxtrader.endpoint
      port     = aws_db_instance.fluxtrader.port
      name     = aws_db_instance.fluxtrader.db_name
      username = aws_db_instance.fluxtrader.username
      password = var.db_master_password
    }
    application = {
      environment = var.environment
      port        = var.app_port
      region      = var.aws_region
    }
    aws = {
      region = var.aws_region
    }
  })
}

output "secrets_manager_arn" {
  description = "AWS Secrets Manager ARN"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

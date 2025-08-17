# Kamikaze-be Infrastructure Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "kamikaze-be"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "app_port" {
  description = "Application port"
  type        = number
  default     = 8000
}

# EC2 Configuration
variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "ec2_public_key" {
  description = "Public key for EC2 access"
  type        = string
}

variable "ec2_volume_size" {
  description = "EC2 root volume size in GB"
  type        = number
  default     = 20
}

# RDS Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS maximum allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "kamikaze"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Application Configuration
variable "docker_image" {
  description = "Docker image for the application"
  type        = string
  default     = "kamikaze-be:latest"
}

variable "container_name" {
  description = "Docker container name"
  type        = string
  default     = "kamikaze-app"
}

# Secrets Manager Configuration
variable "secrets_manager_name" {
  description = "AWS Secrets Manager secret name"
  type        = string
  default     = "kmkz-secrets"
}

# GitHub Configuration (for CI/CD)
variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "Anki246/kamikaze-be"
}

variable "github_branch" {
  description = "GitHub branch for deployment"
  type        = string
  default     = "main"
}

# Monitoring and Logging
variable "enable_detailed_monitoring" {
  description = "Enable detailed monitoring for EC2"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Backup Configuration
variable "backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

# Tags
variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "kamikaze-be"
    ManagedBy   = "terraform"
    Repository  = "https://github.com/Anki246/kamikaze-be"
  }
}

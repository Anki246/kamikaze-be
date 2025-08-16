# Terraform version and provider requirements

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional: Configure remote state backend
  # Uncomment and configure for production use
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "fluxtrader/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# AWS Provider configuration
provider "aws" {
  region = var.aws_region

  # Optional: Configure default tags for all resources
  default_tags {
    tags = {
      Project     = "FluxTrader"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

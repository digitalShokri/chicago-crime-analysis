# Chicago Crime Analysis Project - AWS Infrastructure
# Terraform configuration for secure, scalable deployment

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

  default_tags {
    tags = {
      Project     = "chicago-crime-analysis"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local variables
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  name_prefix        = local.name_prefix
  vpc_cidr          = var.vpc_cidr
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
  
  tags = local.common_tags
}

# Security Module
module "security" {
  source = "./modules/security"
  
  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  
  tags = local.common_tags
}

# Secrets Management Module
module "secrets" {
  source = "./modules/secrets"
  
  name_prefix = local.name_prefix
  
  secrets = {
    anthropic_api_key     = var.anthropic_api_key
    langsmith_api_key     = var.langsmith_api_key
    chicago_data_token    = var.chicago_data_token
  }
  
  tags = local.common_tags
}

# ECR Repository
module "ecr" {
  source = "./modules/ecr"
  
  name_prefix = local.name_prefix
  
  tags = local.common_tags
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  name_prefix     = local.name_prefix
  vpc_id          = module.vpc.vpc_id
  public_subnets  = module.vpc.public_subnet_ids
  security_groups = [module.security.alb_security_group_id]
  
  tags = local.common_tags
}

# ECS Cluster and Service
module "ecs" {
  source = "./modules/ecs"
  
  name_prefix           = local.name_prefix
  vpc_id               = module.vpc.vpc_id
  private_subnets      = module.vpc.private_subnet_ids
  security_groups      = [module.security.ecs_security_group_id]
  target_group_arn     = module.alb.target_group_arn
  ecr_repository_url   = module.ecr.repository_url
  secrets_manager_arns = module.secrets.secret_arns
  
  # Container configuration
  container_cpu    = var.container_cpu
  container_memory = var.container_memory
  desired_count    = var.desired_count
  
  tags = local.common_tags
}

# CloudWatch Logs and Monitoring
module "monitoring" {
  source = "./modules/monitoring"
  
  name_prefix  = local.name_prefix
  cluster_name = module.ecs.cluster_name
  service_name = module.ecs.service_name
  
  tags = local.common_tags
}
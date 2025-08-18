# Variables for Chicago Crime Analysis Project Infrastructure

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "chicago-crime-analysis"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Container Configuration
variable "container_cpu" {
  description = "CPU units for the container (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Memory for the container in MiB"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of container instances"
  type        = number
  default     = 1
}

# Secrets (should be provided via terraform.tfvars or environment variables)
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
  default     = ""
}

variable "langsmith_api_key" {
  description = "LangSmith API key for observability"
  type        = string
  sensitive   = true
  default     = ""
}

variable "chicago_data_token" {
  description = "Chicago Data Portal API token"
  type        = string
  sensitive   = true
  default     = ""
}

# Domain and SSL (optional)
variable "domain_name" {
  description = "Domain name for the application (optional)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN of SSL certificate in ACM (optional)"
  type        = string
  default     = ""
}
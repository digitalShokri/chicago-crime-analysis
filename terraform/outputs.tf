# Outputs for Chicago Crime Analysis Project Infrastructure

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

output "application_url" {
  description = "URL of the deployed application"
  value       = "http://${module.alb.load_balancer_dns_name}"
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = module.alb.load_balancer_dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = module.alb.load_balancer_zone_id
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for the application"
  value       = module.monitoring.log_group_name
}

output "secrets_manager_names" {
  description = "Names of secrets in AWS Secrets Manager"
  value       = module.secrets.secret_names
}

# Security Group IDs for debugging
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = module.security.alb_security_group_id
}

output "ecs_security_group_id" {
  description = "ID of the ECS security group"
  value       = module.security.ecs_security_group_id
}

# Instructions for deployment
output "deployment_instructions" {
  description = "Instructions for completing the deployment"
  value = <<-EOT
  
  🎉 Infrastructure deployed successfully!
  
  Next steps:
  1. Build and push Docker image:
     aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${module.ecr.repository_url}
     docker build -t chicago-crime-analysis .
     docker tag chicago-crime-analysis:latest ${module.ecr.repository_url}:latest
     docker push ${module.ecr.repository_url}:latest
  
  2. Update ECS service to use the new image:
     aws ecs update-service --cluster ${module.ecs.cluster_name} --service ${module.ecs.service_name} --force-new-deployment
  
  3. Access your application:
     URL: http://${module.alb.load_balancer_dns_name}
  
  4. Monitor logs:
     aws logs tail ${module.monitoring.log_group_name} --follow
  
  EOT
}
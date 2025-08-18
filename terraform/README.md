# Chicago Crime Analysis - AWS Deployment

This directory contains Terraform infrastructure code to deploy the Chicago Crime Analysis project to AWS using security best practices.

## 🏗️ Architecture Overview

The deployment creates a secure, scalable infrastructure:

- **ECS Fargate** - Serverless containers (no EC2 management)
- **Application Load Balancer** - SSL termination, health checks
- **VPC with Private Subnets** - Secure network isolation
- **AWS Secrets Manager** - Secure API key storage
- **CloudWatch** - Comprehensive logging and monitoring
- **ECR** - Container image registry

## 🔧 Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform >= 1.0** installed
3. **Docker** installed (for building images)
4. **API Keys** for:
   - Anthropic (Claude)
   - LangSmith (observability)
   - Chicago Data Portal (optional)

## 🚀 Quick Deployment

### 1. Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your API keys and preferences
```

### 2. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy infrastructure
terraform apply
```

### 3. Build and Deploy Application

```bash
# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

# Build Docker image
docker build -t chicago-crime-analysis .

# Tag and push to ECR
docker tag chicago-crime-analysis:latest $(terraform output -raw ecr_repository_url):latest
docker push $(terraform output -raw ecr_repository_url):latest

# Update ECS service to use new image
aws ecs update-service \
    --cluster $(terraform output -raw ecs_cluster_name) \
    --service $(terraform output -raw ecs_service_name) \
    --force-new-deployment
```

### 4. Access Your Application

```bash
echo "Application URL: $(terraform output -raw application_url)"
```

## 📊 Monitoring and Logs

### CloudWatch Dashboard
```bash
echo "Dashboard: $(terraform output -raw monitoring.dashboard_url)"
```

### View Logs
```bash
aws logs tail $(terraform output -raw cloudwatch_log_group) --follow
```

## 🔒 Security Features

- **Private Subnets** - Application runs in isolated network
- **Security Groups** - Minimal required access only
- **Secrets Manager** - API keys stored securely, not in code
- **IAM Roles** - Least privilege access
- **VPC Endpoints** - Private AWS service access
- **Container Scanning** - ECR scans images for vulnerabilities

## 💰 Cost Optimization

The deployment uses cost-effective services:
- **Fargate** - Pay only for running containers
- **NAT Gateways** - Minimal for private subnet access
- **CloudWatch** - Standard monitoring included
- **No EC2** - No always-on server costs

**Estimated monthly cost: $20-50** (depending on usage)

## 🛠️ Configuration Options

### Scaling
```hcl
# In terraform.tfvars
desired_count    = 2     # Multiple container instances
container_cpu    = 1024  # 1 vCPU
container_memory = 2048  # 2 GB RAM
```

### SSL/Domain
```hcl
# In terraform.tfvars
domain_name     = "your-domain.com"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/your-cert"
```

## 📋 Troubleshooting

### Container Won't Start
```bash
# Check ECS service events
aws ecs describe-services \
    --cluster $(terraform output -raw ecs_cluster_name) \
    --services $(terraform output -raw ecs_service_name)

# Check task definition
aws ecs describe-task-definition \
    --task-definition $(terraform output -raw ecs_service_name)
```

### View Application Logs
```bash
aws logs tail $(terraform output -raw cloudwatch_log_group) --follow
```

### Check Secrets
```bash
# List secrets
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `chicago-crime`)].Name'

# Test secret access (from ECS task)
aws secretsmanager get-secret-value --secret-id "chicago-crime-analysis-dev/anthropic-api-key"
```

## 🧹 Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all infrastructure and data. Make sure to backup any important information first.

## 📁 Module Structure

```
terraform/
├── main.tf              # Main infrastructure orchestration
├── variables.tf         # Input variables
├── outputs.tf          # Output values
├── terraform.tfvars    # Your configuration values
└── modules/
    ├── vpc/            # Network infrastructure
    ├── security/       # Security groups
    ├── secrets/        # AWS Secrets Manager
    ├── ecr/            # Container registry
    ├── alb/            # Load balancer
    ├── ecs/            # Container service
    └── monitoring/     # CloudWatch resources
```

## 🔄 Updates and Maintenance

### Update Application Code
1. Build new Docker image
2. Push to ECR with new tag
3. Update ECS service: `aws ecs update-service --force-new-deployment`

### Update Infrastructure
1. Modify Terraform files
2. Run `terraform plan` to review changes
3. Run `terraform apply` to deploy updates

### Security Updates
- ECR automatically scans images for vulnerabilities
- Update base images regularly
- Rotate API keys in Secrets Manager

## 📞 Support

For issues with:
- **Infrastructure**: Check Terraform state and AWS console
- **Application**: Review CloudWatch logs
- **Networking**: Verify security groups and VPC configuration
- **Secrets**: Confirm IAM permissions for Secrets Manager
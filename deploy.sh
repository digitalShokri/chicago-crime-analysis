#!/bin/bash

# Chicago Crime Analysis - AWS Deployment Script
# This script automates the deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if terraform.tfvars exists
    if [[ ! -f "terraform/terraform.tfvars" ]]; then
        log_error "terraform.tfvars not found. Please copy terraform.tfvars.example and configure it."
        exit 1
    fi
    
    log_success "All prerequisites met!"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure..."
    
    cd terraform
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log_info "Planning infrastructure deployment..."
    terraform plan -out=tfplan
    
    # Ask for confirmation
    echo
    read -p "Do you want to apply these changes? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Deployment cancelled."
        exit 0
    fi
    
    # Apply infrastructure
    log_info "Applying infrastructure changes..."
    terraform apply tfplan
    
    # Clean up plan file
    rm -f tfplan
    
    cd ..
    log_success "Infrastructure deployed successfully!"
}

# Build and deploy application
deploy_application() {
    log_info "Building and deploying application..."
    
    # Get ECR repository URL
    ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url)
    REGION=$(cd terraform && terraform output -raw aws_region || echo "us-east-1")
    
    # Login to ECR
    log_info "Logging into ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URL
    
    # Build Docker image
    log_info "Building Docker image..."
    docker build -t chicago-crime-analysis .
    
    # Tag image
    log_info "Tagging image for ECR..."
    docker tag chicago-crime-analysis:latest $ECR_URL:latest
    
    # Push to ECR
    log_info "Pushing image to ECR..."
    docker push $ECR_URL:latest
    
    # Update ECS service
    log_info "Updating ECS service..."
    CLUSTER_NAME=$(cd terraform && terraform output -raw ecs_cluster_name)
    SERVICE_NAME=$(cd terraform && terraform output -raw ecs_service_name)
    
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $REGION
    
    log_success "Application deployed successfully!"
}

# Display deployment information
show_deployment_info() {
    log_info "Deployment Information:"
    echo
    
    cd terraform
    
    APP_URL=$(terraform output -raw application_url)
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    LOG_GROUP=$(terraform output -raw cloudwatch_log_group)
    
    echo "🌐 Application URL: $APP_URL"
    echo "📊 CloudWatch Logs: aws logs tail $LOG_GROUP --follow"
    echo "🔍 ECS Service: $CLUSTER_NAME"
    echo
    
    log_info "Waiting for service to be stable..."
    aws ecs wait services-stable --cluster $CLUSTER_NAME --services $(terraform output -raw ecs_service_name)
    
    log_success "Deployment complete! Your application should be available at: $APP_URL"
    
    cd ..
}

# Main deployment flow
main() {
    echo "🚨 Chicago Crime Analysis - AWS Deployment"
    echo "=========================================="
    echo
    
    check_prerequisites
    deploy_infrastructure
    deploy_application
    show_deployment_info
    
    echo
    log_success "All done! 🎉"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "infrastructure")
        check_prerequisites
        deploy_infrastructure
        ;;
    "application")
        check_prerequisites
        deploy_application
        ;;
    "destroy")
        log_warning "This will destroy ALL infrastructure and data!"
        read -p "Are you absolutely sure? Type 'yes' to confirm: " -r
        if [[ $REPLY == "yes" ]]; then
            cd terraform
            terraform destroy
            log_success "Infrastructure destroyed."
        else
            log_info "Destruction cancelled."
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  deploy          Full deployment (default)"
        echo "  infrastructure  Deploy infrastructure only"
        echo "  application     Deploy application only"
        echo "  destroy         Destroy all infrastructure"
        echo "  help           Show this help message"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information."
        exit 1
        ;;
esac
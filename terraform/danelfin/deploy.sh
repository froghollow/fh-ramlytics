#!/bin/bash

# Danelfin Lambda Deployment Script
# Quick reference for common Terraform operations

set -e

TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TERRAFORM_DIR"

case "${1:-help}" in
  init)
    echo "Initializing Terraform..."
    terraform init
    ;;
  
  plan)
    echo "Planning Terraform deployment..."
    terraform plan -out=tfplan
    ;;
  
  apply)
    echo "Applying Terraform configuration..."
    if [ ! -f tfplan ]; then
      terraform plan -out=tfplan
    fi
    terraform apply tfplan
    rm -f tfplan
    ;;
  
  deploy)
    echo "Full deployment (init + plan + apply)..."
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    rm -f tfplan
    ;;
  
  destroy)
    echo "WARNING: This will destroy all AWS resources!"
    read -p "Are you sure? (yes/no) " -r
    if [[ $REPLY == "yes" ]]; then
      terraform destroy
    else
      echo "Cancelled."
    fi
    ;;
  
  logs)
    echo "Tailing Lambda logs..."
    aws logs tail /aws/lambda/danelfin-ingest-symbols --follow
    ;;
  
  test)
    echo "Testing Lambda function..."
    aws lambda invoke \
      --function-name danelfin-ingest-symbols \
      --payload '{"symbols": ["AAPL", "GOOGL", "MSFT"], "today_str": "2026-06-01"}' \
      /tmp/response.json
    echo "Response:"
    cat /tmp/response.json
    ;;
  
  output)
    echo "Terraform outputs:"
    terraform output -json | jq .
    ;;
  
  status)
    echo "Deployment Status:"
    terraform show
    ;;
  
  clean)
    echo "Cleaning up temporary files..."
    rm -f tfplan lambda_function.zip
    terraform fmt
    ;;
  
  *)
    cat << EOF
Danelfin Lambda Deployment Script

Usage: $0 <command>

Commands:
  init        Initialize Terraform
  plan        Plan the deployment
  apply       Apply the deployment (requires plan)
  deploy      Full deployment (init + plan + apply)
  destroy     Destroy all AWS resources (requires confirmation)
  logs        Tail Lambda execution logs
  test        Test Lambda function with sample event
  output      Display Terraform outputs
  status      Show current deployment status
  clean       Clean temporary files
  help        Show this help message

Examples:
  $0 init           # Initialize Terraform
  $0 deploy         # Deploy to AWS
  $0 logs          # View Lambda logs
  $0 test          # Run test invocation
  $0 destroy       # Tear down infrastructure
EOF
    ;;
esac

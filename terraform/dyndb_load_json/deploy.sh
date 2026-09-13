#!/bin/bash

# dyndb_load_json Lambda Deployment Script
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
    aws logs tail /aws/lambda/ramlytics_dyndb_load_json --follow
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
    rm -f tfplan
    terraform fmt
    ;;

  *)
    echo "Usage: $0 {init|plan|apply|deploy|destroy|logs|output|status|clean}"
    ;;
esac

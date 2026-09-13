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

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current region
data "aws_region" "current" {}

locals {
  function_name = "ramlytics_danelfin_fetch"
  role_name     = "${local.function_name}-lambda-role"
  rule_name     = "${local.function_name}-schedule"
  target_name   = "${local.function_name}-target"
  environment_vars = {
    DANELFIN_API_KEY = var.danelfin_api_key
    S3_BUCKET_NAME   = var.s3_bucket_name
    S3_INBOUND_FOLDER    = var.s3_inbound_folder
  }
}

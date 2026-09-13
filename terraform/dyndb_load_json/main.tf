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
  function_name = "ramlytics_dyndb_load_json"
  role_name     = "${local.function_name}-lambda-role"
  layer_name    = "${local.function_name}-deps"
  environment_vars = {
    DYNAMODB_TABLE     = var.dynamodb_table_name
    DEFAULT_AWS_REGION = var.aws_region
  }
}

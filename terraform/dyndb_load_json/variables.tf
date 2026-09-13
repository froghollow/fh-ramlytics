variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "lambda_function_zip" {
  description = "Path to the Lambda function code package (handler only), relative to this module"
  type        = string
  default     = "../../backend/dyndb_load_json/lambda_function.zip"
}

variable "lambda_layer_zip" {
  description = "Path to the Lambda layer package (dependencies), relative to this module"
  type        = string
  default     = "../../backend/dyndb_load_json/lambda_layer.zip"
}

variable "deployment_artifact_prefix" {
  description = "S3 key prefix used to stage Lambda deployment zips before publishing"
  type        = string
  default     = "lambda-artifacts/dyndb_load_json"
}

variable "s3_bucket_name" {
  description = "S3 bucket that market data JSON files land in"
  type        = string
  default     = "fh-danelfin-289755104220"
}

variable "s3_key_prefix" {
  description = "S3 key prefix to watch for incoming market data files"
  type        = string
  default     = "ingest/market_data/"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name used by ramlytics_database"
  type        = string
  default     = "alex-financial-data"
}

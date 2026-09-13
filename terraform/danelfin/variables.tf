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
  default     = 300
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "lambda_function_zip" {
  description = "Path to the Lambda deployment package, relative to this module"
  type        = string
  default     = "../../backend/danelfin/lambda_function.zip"
}

variable "s3_bucket_name" {
  description = "S3 bucket for storing Danelfin data"
  type        = string
  default     = "fh-danelfin-289755104220"
}

variable "s3_inbound_folder" {
  description = "S3 key prefix for stored data"
  type        = string
  default     = "inbound/market_data"
}

variable "danelfin_api_key" {
  description = "Danelfin API key"
  type        = string
  sensitive   = true
}

variable "symbols" {
  description = "List of stock symbols to ingest"
  type        = list(string)
  default = [
    "AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA",
    "JNJ", "WMT", "PLTR", "AVGO", "VYM", "QQQ", "SPY",
    "IWD", "IVW", "XLK", "GLD", "SLV", "VXX", "AGGH", "FSTA"
  ]
}

variable "schedule_timezone" {
  description = "Timezone for the schedule (default is America/New_York for EDT)"
  type        = string
  default     = "America/New_York"
}

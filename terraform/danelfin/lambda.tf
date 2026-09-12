# Archive the Lambda function code
#data "archive_file" "lambda_zip" {
#  type        = "zip"
#  source_dir  = "${path.module}/lambda_package"
#  output_path = "${path.module}/lambda_function.zip"
#}

# Lambda Function
resource "aws_lambda_function" "danelfin_fetch" {
  filename         = "${path.module}/${var.lambda_function_zip}"
  source_code_hash = fileexists("${path.module}/${var.lambda_function_zip}") ? filebase64sha256("${path.module}/${var.lambda_function_zip}") : null

  function_name    = local.function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "danelfin_fetch.lambda_handler"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  runtime          = "python3.12"

  environment {
    variables = local.environment_vars
  }

  depends_on = [
    aws_iam_role_policy.lambda_s3_policy,
    aws_iam_role_policy_attachment.lambda_basic_execution
  ]

  layers = []

  # Optional: add VPC configuration if needed
  # vpc_config {
  #   subnet_ids         = var.subnet_ids
  #   security_group_ids = var.security_group_ids
  # }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14
}

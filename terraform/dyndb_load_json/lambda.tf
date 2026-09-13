# The dependency layer zip is too large for Lambda's direct-upload API (~70MB request limit),
# so upload both artifacts to S3 and reference them from there instead (250MB unzipped limit).
resource "aws_s3_object" "lambda_layer_zip" {
  bucket = var.s3_bucket_name
  key    = "${var.deployment_artifact_prefix}/lambda_layer.zip"
  source = "${path.module}/${var.lambda_layer_zip}"
  etag   = filemd5("${path.module}/${var.lambda_layer_zip}")
}

resource "aws_s3_object" "lambda_function_zip" {
  bucket = var.s3_bucket_name
  key    = "${var.deployment_artifact_prefix}/lambda_function.zip"
  source = "${path.module}/${var.lambda_function_zip}"
  etag   = filemd5("${path.module}/${var.lambda_function_zip}")
}

# Lambda Layer - third-party + workspace dependencies (built by backend/dyndb_load_json/package.py)
resource "aws_lambda_layer_version" "dependencies" {
  s3_bucket           = aws_s3_object.lambda_layer_zip.bucket
  s3_key              = aws_s3_object.lambda_layer_zip.key
  source_code_hash    = filebase64sha256("${path.module}/${var.lambda_layer_zip}")
  layer_name          = local.layer_name
  compatible_runtimes = ["python3.12"]
}

# Lambda Function - handler code only, dependencies come from the layer above
resource "aws_lambda_function" "dyndb_load_json" {
  s3_bucket        = aws_s3_object.lambda_function_zip.bucket
  s3_key           = aws_s3_object.lambda_function_zip.key
  source_code_hash = filebase64sha256("${path.module}/${var.lambda_function_zip}")

  function_name = local.function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "dyndb_load_json.lambda_handler"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory
  runtime       = "python3.12"

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.environment_vars
  }

  depends_on = [
    aws_iam_role_policy.lambda_s3_policy,
    aws_iam_role_policy.lambda_dynamodb_policy,
    aws_iam_role_policy_attachment.lambda_basic_execution
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14
}

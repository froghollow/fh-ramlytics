# S3 trigger - invoke the Lambda when new market data JSON files land under the watched prefix
resource "aws_s3_bucket_notification" "data_ingest" {
  bucket = var.s3_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.dyndb_load_json.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.s3_inbound_folder
    filter_suffix       = ".msReportCard.json"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.dyndb_load_json.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.s3_inbound_folder
    filter_suffix       = ".ai_scores.json"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.dyndb_load_json.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.s3_inbound_folder
    filter_suffix       = ".trading_params.json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# EventBridge Rule - Schedule for MON-FRI at 6am EDT (10am UTC)
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = local.rule_name
  description         = "Trigger Danelfin symbol ingestion MON-FRI at 6am EDT"
  schedule_expression = "cron(0 10 ? * MON-FRI *)"
  state               = "ENABLED"

  # Optional: Configure timezone (requires EventBridge Scheduler for timezone support)
  # For now, using UTC conversion: 6am EDT = 10am UTC
}

# EventBridge Target - Lambda function
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = local.target_name
  arn       = aws_lambda_function.danelfin_fetch.arn

  # Pass the symbols list as event input to Lambda
  input = jsonencode({
    symbols    = var.symbols
    today_str  = null  # Lambda will use current date if not provided
  })
}

# CloudWatch Event Rule (alias for EventBridge Rule)
output "event_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.schedule.name
}

output "event_rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.schedule.arn
}

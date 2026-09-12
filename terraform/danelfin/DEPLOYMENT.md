# Step-by-Step Deployment Guide

## Prerequisites Checklist

- [ ] AWS CLI installed and configured (`aws --version`)
- [ ] Terraform installed (`terraform --version`)
- [ ] Danelfin API key available
- [ ] AWS S3 bucket created or ready to use
- [ ] AWS IAM permissions to create Lambda, IAM roles, EventBridge

## Step 1: Prepare Configuration

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# Required: Your Danelfin API key
danelfin_api_key = "your-api-key-here"

# AWS configuration
aws_region      = "us-east-1"
environment     = "production"

# S3 configuration
s3_bucket_name = "your-bucket-name"
s3_key_prefix  = "json/"

# Lambda configuration (optional)
lambda_timeout = 300
lambda_memory  = 512

# Stock symbols to ingest (optional)
symbols = [
  "AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA",
  "JNJ", "WMT", "PLTR", "AVGO", "VYM", "QQQ", "SPY",
  "IWD", "IVW", "XLK", "GLD", "SLV", "VXX", "AGGH", "FSTA"
]
```

## Step 2: Verify AWS Credentials

```bash
# Verify you're authenticated to the correct AWS account
aws sts get-caller-identity

# Output should show your Account ID, User ARN, etc.
```

## Step 3: Initialize Terraform

```bash
terraform init
```

This downloads the required AWS provider and prepares your Terraform working directory.

## Step 4: Plan the Deployment

```bash
terraform plan -out=tfplan
```

Review the output to ensure:
- Lambda function is being created
- IAM role and policies are correct
- EventBridge rule is scheduled correctly
- CloudWatch log group is created

## Step 5: Apply the Deployment

```bash
terraform apply tfplan
```

This creates all AWS resources. You should see:
- Lambda function created
- IAM role created
- EventBridge rule created
- CloudWatch log group created

Note the outputs displayed at the end:
```
Outputs:

lambda_function_arn = "arn:aws:lambda:us-east-1:ACCOUNT:function:ramlytics-danelfin-fetch"
lambda_function_name = "ramlytics-danelfin-fetch"
eventbridge_rule_arn = "arn:aws:events:us-east-1:ACCOUNT:rule/ramlytics-danelfin-fetch-schedule"
...
```

## Step 6: Verify Deployment

### Check Lambda Function

```bash
aws lambda get-function --function-name danelfin-ingest-symbols
```

### Check EventBridge Rule

```bash
aws events describe-rule --name danelfin-ingest-symbols-schedule
```

You should see:
- `State: ENABLED`
- `ScheduleExpression: "cron(0 10 ? * MON-FRI *)"`

### Test Lambda Manually

```bash
# Test with sample data
aws lambda invoke \
  --function-name danelfin-ingest-symbols \
  --payload '{
    "symbols": ["AAPL", "GOOGL"],
    "today_str": "2026-06-01"
  }' \
  response.json

cat response.json
```

Or use the convenience script:

```bash
./deploy.sh test
```

### View Logs

```bash
# Option 1: Tail logs in real-time
aws logs tail /aws/lambda/danelfin-ingest-symbols --follow

# Option 2: View last 50 lines
aws logs tail /aws/lambda/danelfin-ingest-symbols --max-items 50

# Option 3: Use convenience script
./deploy.sh logs
```

## Step 7: Monitor Schedule

The Lambda will automatically run at 6:00 AM EDT (10:00 AM UTC) on weekdays.

### Check Last Executions

```bash
aws lambda get-function-concurrency --function-name danelfin-ingest-symbols
```

### List Invocations

```bash
aws logs describe-log-streams \
  --log-group-name /aws/lambda/danelfin-ingest-symbols \
  --order-by LastEventTime \
  --descending
```

## Step 8: Verify S3 Data

Check that data is being stored correctly:

```bash
# List recent files
aws s3 ls s3://your-bucket-name/json/ --recursive --human-readable | tail -20

# Download a sample file
aws s3 cp s3://your-bucket-name/json/2026-06-01.AAPL.json ./
cat 2026-06-01.AAPL.json | jq .
```

## Troubleshooting

### Lambda Function Not Triggering

1. **Check EventBridge rule is enabled:**
   ```bash
   aws events describe-rule --name danelfin-ingest-symbols-schedule
   ```
   Look for `"State": "ENABLED"`

2. **Check Lambda permission exists:**
   ```bash
   aws lambda get-policy --function-name danelfin-ingest-symbols
   ```

3. **View EventBridge target:**
   ```bash
   aws events list-targets-by-rule --rule danelfin-ingest-symbols-schedule
   ```

### Lambda Execution Fails

1. **Check logs:**
   ```bash
   ./deploy.sh logs
   ```

2. **Check IAM permissions:**
   ```bash
   aws iam get-role-policy \
     --role-name danelfin-ingest-symbols-lambda-role \
     --policy-name danelfin-ingest-symbols-s3-policy
   ```

3. **Test with simpler payload:**
   ```bash
   aws lambda invoke \
     --function-name danelfin-ingest-symbols \
     --payload '{"symbols": ["AAPL"]}' \
     response.json
   ```

### Import Errors

If you see import errors in logs:

1. **Check danelfin module is installed:**
   The Lambda layer should include the danelfin module. If missing, update `lambda_package/requirements.txt` and redeploy:
   ```bash
   terraform apply
   ```

2. **Verify environment variables:**
   ```bash
   aws lambda get-function-config --function-name danelfin-ingest-symbols | jq '.Environment'
   ```

### S3 Upload Failures

1. **Verify bucket exists:**
   ```bash
   aws s3 ls s3://your-bucket-name
   ```

2. **Check bucket permissions:**
   ```bash
   aws s3api head-bucket --bucket your-bucket-name
   ```

3. **Check IAM policy:**
   Review the policy in `iam.tf` and verify S3 actions are allowed

## Maintenance

### Update Lambda Code

1. Modify `lambda_package/lambda_handler.py`
2. Update version if needed
3. Redeploy:
   ```bash
   terraform apply
   ```

### Update Symbols List

Edit `terraform.tfvars`:
```hcl
symbols = ["AAPL", "GOOGL", "MSFT", "AMZN"]
```

Then redeploy:
```bash
terraform apply
```

### Change Schedule

Edit `eventbridge.tf` and modify `schedule_expression`:
```hcl
schedule_expression = "cron(0 16 ? * MON-FRI *)"  # 4pm UTC (12pm EDT)
```

Then redeploy:
```bash
terraform apply
```

### Increase Lambda Timeout

Edit `terraform.tfvars`:
```hcl
lambda_timeout = 600  # 10 minutes instead of 5
```

Then redeploy:
```bash
terraform apply
```

## Cleanup

To remove all AWS resources:

```bash
terraform destroy
```

Confirm by typing `yes` when prompted. This will delete:
- Lambda function
- IAM role and policies
- EventBridge rule
- CloudWatch log group

**Warning**: This cannot be undone. Make sure you have backups of any data stored in S3.

## Next Steps

1. **Production Hardening:**
   - Use AWS Secrets Manager for API key storage
   - Add VPC configuration if needed
   - Enable Lambda function URL monitoring
   - Set up SNS alerts for failures

2. **Optimize Performance:**
   - Adjust Lambda memory based on monitoring
   - Optimize sleep delays between API calls
   - Consider batching symbol requests

3. **Enhance Error Handling:**
   - Add retry logic for failed API calls
   - Set up Dead Letter Queue (DLQ) for failed invocations
   - Send notifications on failures

## Quick Reference Commands

```bash
# Deploy everything
./deploy.sh deploy

# View logs
./deploy.sh logs

# Test manually
./deploy.sh test

# See outputs
./deploy.sh output

# Destroy (with confirmation)
./deploy.sh destroy

# Show current state
./deploy.sh status

# Format code
./deploy.sh clean
```

## Additional Resources

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [AWS EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/)
- [Terraform Best Practices](https://developer.hashicorp.com/terraform/cloud-docs/recommended-practices)

# Terraform Deployment: Danelfin Fetch Lambda

This Terraform configuration deploys an AWS Lambda function that retrieves Danelfin rankings for a list of stock symbols on a schedule and stores the results in S3.

## Architecture

- **Lambda Function**: `danelfin-fetch` runs the data ingestion
- **EventBridge Rule**: Triggers the Lambda on a schedule (MON-FRI at 6am EDT / 10am UTC)
- **IAM Role**: Grants Lambda permissions to access S3 and write logs
- **S3 Integration**: Stores JSON ranking data with date-based prefixes
- **CloudWatch Logs**: Captures Lambda execution logs

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** installed (>= 1.0)
3. **AWS CLI** configured with credentials
4. **Danelfin API Key** (set as environment variable or in tfvars)
5. **S3 Bucket** for storing data (created beforehand or by Terraform)

## Setup

### 1. Create Configuration File

Copy the example and add your credentials:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
aws_region           = "us-east-1"
danelfin_api_key     = "your-danelfin-api-key"
s3_bucket_name       = "your-bucket-name"
environment          = "production"

# Optional: customize symbols
symbols = [
  "FSTA", "GLD", "HODL"
]
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Review the Deployment Plan

```bash
terraform plan
```

### 4. Deploy

```bash
terraform apply
```

Confirm by typing `yes` when prompted.

## Configuration

### Environment Variables

The Lambda function uses these environment variables (set automatically):
- `DANELFIN_API_KEY`: Your Danelfin API key
- `S3_BUCKET_NAME`: S3 bucket for storing data
- `S3_INBOUND_FOLDER`: Prefix for S3 keys (default: `json/`)

### Schedule

The EventBridge rule triggers at:
- **Time**: 6:00 AM EDT (10:00 AM UTC)
- **Days**: Monday through Friday
- **Cron Expression**: `cron(0 10 ? * MON-FRI *)`

To change the schedule, modify the `schedule_expression` in `eventbridge.tf`.

### Lambda Configuration

Adjust these variables if needed:
- `lambda_timeout`: Execution timeout in seconds (default: 300)
- `lambda_memory`: Memory allocation in MB (default: 512)

## Deployment Details

### Lambda Package Structure

The deployment package includes:
```
lambda_package/
├── lambda_handler.py          # Entry point
└── requirements.txt           # Python dependencies
```

The Danelfin module and dependencies are installed during deployment.

### IAM Permissions

The Lambda role has:
- S3 read/write access to the specified bucket
- CloudWatch Logs write access
- Basic Lambda execution permissions

## Monitoring

### View Lambda Logs

```bash
aws logs tail /aws/lambda/danelfin-fetch --follow
```

### List Recent Executions

```bash
aws lambda get-function-concurrency --function-name danelfin-fetch
```

### Test the Lambda Manually

```bash
aws lambda invoke \
  --function-name danelfin-fetch \
  --payload '{"symbols": ["AAPL", "GOOGL"]}' \
  response.json

cat response.json
```

## Troubleshooting

### Import Errors

If you see `ImportError: cannot import name 'DanelfinClient'`:
- Ensure `danelfin` package is in the Lambda layer or dependencies
- Check that the module path is correct in `lambda_handler.py`

### S3 Upload Failures

- Verify S3 bucket exists and bucket name is correct
- Check IAM role has S3 permissions
- Ensure `s3:PutObject` action is allowed in the policy

### Lambda Timeout

If the function times out:
- Increase `lambda_timeout` variable
- Check Danelfin API response times
- Monitor sleep delays between requests

### EventBridge Not Triggering

- Verify the rule is enabled (check AWS console)
- Check that the Lambda permission for EventBridge exists
- Review CloudWatch Events rule in AWS console

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

Confirm by typing `yes` when prompted.

## Outputs

After deployment, Terraform outputs:
- `lambda_function_arn`: ARN of the Lambda function
- `lambda_function_name`: Function name
- `eventbridge_rule_arn`: ARN of the EventBridge rule
- `cloudwatch_log_group`: CloudWatch log group name
- `deployment_info`: Summary of deployment settings

## Security Best Practices

1. **Store API Keys Securely**: Use AWS Secrets Manager for production
2. **Rotate Credentials**: Regularly rotate Danelfin API key
3. **Least Privilege**: The Lambda role only has S3 access to the specified bucket
4. **Logs**: CloudWatch logs are retained for 14 days (configurable)
5. **Encryption**: Enable S3 bucket encryption at rest

### Using AWS Secrets Manager (Optional)

For production, store the API key in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name danelfin/api-key \
  --secret-string "your-api-key"
```

Then update `lambda_handler.py` to retrieve from Secrets Manager:

```python
import boto3
secrets_client = boto3.client('secretsmanager')
response = secrets_client.get_secret_value(SecretId='danelfin/api-key')
danelfin_api_key = response['SecretString']
```

## File Structure

```
terraform/
├── main.tf                    # Provider and local variables
├── variables.tf               # Input variables
├── lambda.tf                  # Lambda function resource
├── iam.tf                     # IAM roles and policies
├── eventbridge.tf             # EventBridge schedule and target
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example configuration
└── lambda_package/
    ├── lambda_handler.py      # Lambda entry point
    └── requirements.txt       # Python dependencies
```

## Support

For issues or questions:
1. Check CloudWatch Logs: `/aws/lambda/danelfin-fetch`
2. Review the Terraform state: `terraform show`
3. Test Lambda manually with sample event
4. Verify AWS credentials and permissions

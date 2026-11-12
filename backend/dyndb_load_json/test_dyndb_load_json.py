"""Local test for dyndb_load_json.lambda_handler using real S3 and DynamoDB (boto3).

If the S3 object does not exist, it is first uploaded from --body-file (or a built-in
sample), then the handler is invoked with a simulated S3 ObjectCreated event. The
handler moves the object to ingest/<folder>/<today>/ after processing.

Example (from backend/dyndb_load_json):
    uv run --with boto3 --with-editable ../database python test_dyndb_load_json.py \
        inbound/market_data/AAPL.ai_scores.json --body-file aapl.json

DynamoDB settings come from DYNAMODB_TABLE (default alex-financial-data),
DEFAULT_AWS_REGION / AWS_REGION and your normal AWS credentials.
The key's parent folder (market_data / account_data) selects the handler branch.
"""
import argparse
import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BUCKET = os.getenv("S3_BUCKET", "fh-danelfin-289755104220")
DEFAULT_KEY = "/ingest/account_data/2026-10-15/SFM-ROLL--8322.etrade.json"
SAMPLE_BODY = {"symbol": "AAPL", "aiscore": 8}

def make_s3_event(bucket: str, key: str) -> dict:
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {"name": bucket}, "object": {"key": key}},
            }
        ]
    }

def ensure_object(s3, bucket: str, key: str, body: dict) -> None:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        print(f"Using existing s3://{bucket}/{key}")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
            raise
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(body).encode("utf-8"))
        print(f"Uploaded test object s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("key", nargs="?", default=DEFAULT_KEY)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--body-file", help="local JSON file to upload if the object is missing")
    args = parser.parse_args()

    body = SAMPLE_BODY
    if args.body_file:
        with open(args.body_file) as f:
            body = json.load(f)

    ensure_object(boto3.client("s3"), args.bucket, args.key, body)

    from dyndb_load_json import lambda_handler

    print(f"DynamoDB table={os.getenv('DYNAMODB_TABLE', 'alex-financial-data')}")
    result = lambda_handler(make_s3_event(args.bucket, args.key), None)
    print("Result:", result)


if __name__ == "__main__":
    main()

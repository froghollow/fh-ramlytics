# local test dyndb_import_json_to_instruments.py
import os

from backend.market_data_json_loader import lambda_handler

outpath = os.getenv("OUTPATH", "/tmp/accounts") 

import boto3
s3_bucket = os.getenv("S3_BUCKET", "fh-danelfin-289755104220")
s3_inbound_folder = "inbound/"
s3_client = boto3.client("s3")

# for each .json in the s3 bucket under the key prefix
response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_inbound_folder)
for obj in response.get("Contents", []):
    key = obj["Key"]

    # process only files in root folder
    if "/" in key[len(s3_inbound_folder):]:
        continue

    if key.endswith(".json") :
        #print(f"Found JSON file: s3://{s3_bucket}/{key}")

        # emulate an s3 ObjectCreated event for the lambda handler
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": s3_bucket},
                        "object": {"key": key},
                    }
                }
            ]
        }
        lambda_handler(event, None) # local test

print("Finished processing all JSON files.")


"""
etrade_store_account.py  
Lambda triggered by S3 ObjectCreate event stores json account data into DynamoDB, including account and position data.
If the instrument is not already in the DB, it is added.
"""
import boto3
import os
import json

from tomlkit import key
import dynamodb_client

from decimal import Decimal

s3_client = boto3.client("s3", region_name="us-east-1")
s3_bucket_name = os.getenv("S3_BUCKET_NAME", "fh-danelfin-289755104220")
s3_key_prefix = os.getenv("S3_KEY_PREFIX", "ingest/accounts")
clerk_user_id = os.getenv("CLERK_USER_ID", "user_3DM8poEbvBf5VXyVG4AGF9bdnoe") # Richard & Sue
context=None # local context for testing outside of Lambda

db = dynamodb_client.DynamoDBClient()

# lambda handler for S3 ObjectCreate event
def lambda_handler(event, context):
    for record in event["Records"]:
        s3_object_key = record["s3"]["object"]["key"]
        s3_object = s3_client.get_object(Bucket=s3_bucket_name, Key=s3_object_key)
        json_account = json.loads(s3_object["Body"].read().decode("utf-8"))
        #clerk_user_id = clerk_user_id
        account_id = json_account["account_id"]
        print(f"Processing account {account_id} for clerk user {clerk_user_id}")
        print(f"JSON account data: {json_account}")

        db.put_account(
            clerk_user_id  = clerk_user_id,
            account_id     = account_id,
            id            = account_id,  # ??? 
            cash_balance   = json_account['header'][account_id]['Cash_Purchasing_Power'],
            account_name   = json_account["account_name"],
            account_purpose = json_account["account_purpose"],
            instruments    = json_account["symbols"],
            header        = json_account["header"],
            holdings      = json_account["holdings"]
        )

        for symbol in json_account["symbols"]:
            print(symbol)

            holding = json_account["holdings"][symbol]

            instrument = db.get_instrument(symbol)
            if not instrument:
                print(f"Instrument {symbol} not found in DB. Adding it.")
                db.put_instrument(
                    symbol = symbol,
                    comment = f"imported from E*Trade account {json_account['account_name']}"
                )
                instrument = db.get_instrument(symbol)
            
            #instrument.pop("symbol")
            instrument['current_price'] = holding.get("Last_Price_Amt", Decimal("0.00"))
            db.put_instrument(**instrument)

            position = db.get_position(
                account_id=account_id,
                symbol=symbol
            )
            if not position:
                print(f"Position for {symbol} in account {account_id} not found. Creating it.")
                db.put_position(
                    clerk_user_id=clerk_user_id,
                    account_id=account_id,
                    symbol=symbol,
                    quantity=Decimal(str(holding.get("Quantity", "0.00"))),  # Default to 0 quantity
                    holding=holding,
                )
                position = db.get_position(
                    account_id=account_id,
                    symbol=symbol
                )
            else:
                position['quantity'] = Decimal(str(holding.get("Quantity", "0.00")))
                position['holding'] = holding
                db.put_position(**position)

        # move the processed file to a "./yyyy-mm-dd" folder in the s3 bucket
        from datetime import datetime
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        new_key = f"{s3_key_prefix}/{date_prefix}/{s3_object_key.split('/')[-1]}"
        print(f"Moving processed {s3_object_key} to {new_key}")
        s3_client.copy_object(Bucket=s3_bucket_name, CopySource={"Bucket": s3_bucket_name, "Key": s3_object_key}, Key=new_key)
        s3_client.delete_object(Bucket=s3_bucket_name, Key=s3_object_key)  # delete the original file after moving

        # Return a success response after processing all symbols
        return {
            "statusCode": 200,
            "body": json.dumps("Processed json content successfully!")
        }
# Market Data JSON Loader -- ToDo implement as Lambda function
import json
import boto3
from urllib.parse import unquote_plus
import os

from ramlytics_database import DynamoDBClient
db = DynamoDBClient()

from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")

s3 = boto3.client("s3")

s3_ingest_folder  = os.getenv("S3_INGEST_FOLDER", f"ingest/market_data/{today}")

def move_processed_file(s3_bucket_name, s3_key, s3_ingest_folder):
    new_key = f"{s3_ingest_folder}/{s3_key.split('/')[-1]}"
    
    s3.copy_object(Bucket=s3_bucket_name, CopySource={"Bucket": s3_bucket_name, "Key": s3_key}, Key=new_key)
    s3.delete_object(Bucket=s3_bucket_name, Key=s3_key)

    print(f"Moving file to {new_key}")

    return new_key

def lambda_handler(event, context):
    from datetime import datetime

    s3_bucket_name = event['Records'][0]['s3']['bucket']['name']
    s3_key = unquote_plus(event['Records'][0]['s3']['object']['key'])
    s3_ingest_folder = f"ingest/{s3_key.split('/')[-2]}/{today}"

    print(s3_key)
    if s3_key.endswith('.msReportCard.json'):
        print(f"Morgan Stanley report card: {s3_key}")
    elif s3_key.endswith('.ai_scores.json'):
        print(f"Danelfin AI scores: {s3_key}")
    elif s3_key.endswith('.trading_params.json'):
        print(f"Danelfin Trading Params: {s3_key}")
    elif s3_key.endswith('.price_forecast.json'):
        print(f"Danelfin Price Forecast: {s3_key}")
    elif s3_key.endswith('dfin_top100.json'):
        print(f"Danelfin Top 100: {s3_key} -- (unused for now)")
        move_processed_file(s3_bucket_name, s3_key, s3_ingest_folder)
        return
    elif s3_key.endswith('dfin_trade_ideas.json'):
        print(f"Danelfin Trade Ideas: {s3_key} -- (unused for now)")
        move_processed_file(s3_bucket_name, s3_key, s3_ingest_folder)
        return
    else:
        print(f"Skipping unknown file type: {s3_key}")
        return

    # read the file from S3
    response = s3.get_object(Bucket=s3_bucket_name, Key=s3_key)
    content = response['Body'].read().decode('utf-8')
    timestamp = datetime.now().isoformat(sep=' ')
    
    try:
        parsed_content = json.loads(content)
        print(f"Parsed JSON content of {s3_key}:")
        print(parsed_content)
        parsed_content["updated_at"] = timestamp
    except json.JSONDecodeError:
        print(f"Failed to parse JSON content of {s3_key}")

    if "market_data" in s3_ingest_folder:  # ToDo: deploy/test Sep 20 mods)
        symbol = parsed_content.get("symbol")
        instrument = db.get_instrument(symbol)
        if not instrument:
            print(f"Instrument {symbol} not found in DB. Adding it.")
            db.put_instrument(
                symbol=symbol
            )
            instrument = db.get_instrument(symbol)
        
        instrument.update(parsed_content)
        instrument.pop("symbol")
        db.put_instrument(symbol, **instrument)
        
    elif "accounts" in s3_ingest_folder:  # ToDo: deploy/test Sep 20 mods)
        clerk_user_id = parsed_content.get("clerk_user_id")
        account_id = parsed_content.get("account_id")
        account = db.get_account(clerk_user_id, account_id)
        if not account:
            print(f"Account {account_id} for user {clerk_user_id} not found in DB. Adding it.")
            db.put_account(
                clerk_user_id=clerk_user_id,
                account_id=account_id,
                id=account_id,  # ??? 
            )
            account = db.get_account(clerk_user_id, account_id)
        
        account.update(parsed_content)
        account.pop("clerk_user_id")
        account.pop("account_id")
        db.put_account(clerk_user_id, account_id, **account)


    # move the processed file to a "./yyyy-mm-dd" folder in the s3 bucket
    move_processed_file(s3_bucket_name, s3_key, s3_ingest_folder)

    return {
        "statusCode": 200,
        "body": json.dumps("Processed json content successfully!")
    }

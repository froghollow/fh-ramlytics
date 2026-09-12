# Market Data JSON Loader -- ToDo implement as Lambda function
import json
import boto3
from datetime import datetime

from ramlytics_database import DynamoDBClient
db = DynamoDBClient()

s3 = boto3.client("s3")
bucket_name = "fh-danelfin-289755104220"
prefix = "ingest/market_data/"

def lambda_handler(event, context):
    from datetime import datetime

    key = event['Records'][0]['s3']['object']['key']
    bucket_name = event['Records'][0]['s3']['bucket']['name']

    print(key)
    if key.endswith('.msReportCard.json'):
        print(f"Morgan Stanley report card: {key}")
    elif key.endswith('.ai_scores.json'):
        print(f"Danelfin AI scores: {key}")
    elif key.endswith('.trading_params.json'):
        print(f"Danelfin Trading Params: {key}")
    #elif key.endswith('.price_forecast.json'):
    #    print(f"Danelfin Price Forecast: {key}")
    else:
        print(f"Skipping Unknown file type: {key}")
        return

    # read the file from S3
    response = s3.get_object(Bucket=bucket_name, Key=key)
    content = response['Body'].read().decode('utf-8')
    timestamp = datetime.now().isoformat(sep=' ')
    
    try:
        parsed_content = json.loads(content)
        print(f"Parsed JSON content of {key}:")
        print(parsed_content)
        parsed_content["updated_at"] = timestamp
    except json.JSONDecodeError:
        print(f"Failed to parse JSON content of {key}")

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

    # move the processed file to a "./yyyy-mm-dd" folder in the s3 bucket
    from datetime import datetime
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    new_key = f"{prefix}{date_prefix}/{key.split('/')[-1]}"
    print(f"Moving processed file to {new_key}")
    s3.copy_object(Bucket=bucket_name, CopySource={"Bucket": bucket_name, "Key": key}, Key=new_key)
    s3.delete_object(Bucket=bucket_name, Key=key)

    return {
        "statusCode": 200,
        "body": json.dumps("Processed json content successfully!")
    }

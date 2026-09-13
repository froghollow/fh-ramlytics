"""
Lambda handler wrapper for Danelfin symbol ingestion.
This file serves as the entry point for AWS Lambda.
"""

import json
import os
import sys
import datetime
from time import sleep
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)


def handler(event, context):
    """
    AWS Lambda handler for ingesting Danelfin rankings and storing in S3.
    
    Args:
        event: Lambda event object containing:
            - symbols: list of stock symbols to ingest
            - today_str: (optional) date string in YYYY-MM-DD format
        context: Lambda context object
    
    Returns:
        dict: statusCode and body with result message
    """
    from danelfin import DanelfinClient
    
    s3_client = boto3.client("s3", region_name="us-east-1")
    
    # Get parameters from event
    today_str = event.get("today_str", datetime.date.today().strftime("%Y-%m-%d"))
    symbols = event.get("symbols", [])
    
    print(f"Retrieving data for date: {today_str}")
    print(f"Processing {len(symbols)} symbols")
    
    # Load configuration from environment
    danelfin_api_key = os.getenv("DANELFIN_API_KEY")
    s3_bucket_name = os.getenv("S3_BUCKET_NAME", "fh-danelfin-289755104220")
    s3_inbound_folder = os.getenv("S3_INBOUND_FOLDER", "json/")
    
    if not danelfin_api_key:
        raise ValueError("DANELFIN_API_KEY environment variable is required")
    
    if not symbols:
        raise ValueError("symbols list is required in event")
    
    # Initialize Danelfin client
    client = DanelfinClient(api_key=danelfin_api_key)
    
    try:
        # Ingest individual symbols
        for symbol in symbols:
            fname = f"{s3_inbound_folder}{today_str}.{symbol}.json"
            print(f"Fetching scores for {symbol}...")
            
            try:
                score = client.ranking(date=today_str, ticker=symbol)
                
                # Save locally first (Lambda has /tmp)
                local_path = f"/tmp/{today_str}.{symbol}.json"
                with open(local_path, "w") as f:
                    json.dump(score, f, indent=4)
                
                # Upload to S3
                s3_client.upload_file(local_path, s3_bucket_name, fname)
                print(f"Successfully uploaded {symbol}")
                
                sleep(1)  # Brief pause to avoid rate limits
                
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                # Continue with next symbol on error
                continue
        
        # Ingest TOP_100
        fname = f"{s3_inbound_folder}{today_str}.TOP_100.json"
        print(f"Fetching TOP_100 rankings...")
        
        top_100 = client.ranking(date=today_str)
        local_path = f"/tmp/{today_str}.TOP_100.json"
        with open(local_path, "w") as f:
            json.dump(top_100, f, indent=4)
        
        s3_client.upload_file(local_path, s3_bucket_name, fname)
        print("Successfully uploaded TOP_100")
        
        return {
            "statusCode": 200,
            "body": json.dumps("Danelfin data fetched and stored in S3 successfully!")
        }
        
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error: {str(e)}")
        }

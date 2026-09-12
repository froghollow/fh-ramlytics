"""
danelfin_fetch.py: Lambda function to fetch Danelfin rankings into .json files 
"""

def save_and_upload_json(fname, json_data):
    import boto3
    import json
    import os
    from time import sleep
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_bucket_name = os.getenv("S3_BUCKET_NAME", "fh-danelfin-289755104220")
    s3_key_prefix  = os.getenv("S3_KEY_PREFIX", "ingest/market_data")
    ingest_path = os.getenv("INGEST_PATH", "/tmp")

    with open(f"{ingest_path}/{fname}", "w") as f:
        json.dump(json_data, f, indent=4)
    s3_client.upload_file(f"{ingest_path}/{fname}", s3_bucket_name, f"{s3_key_prefix}/{fname}")

    print(f"Saved and uploaded {fname} to S3 bucket {s3_bucket_name}")
    sleep(10)  # Sleep for 10 seconds to avoid hitting rate limits

def lambda_handler(event, context=None):
    import os
    from danelfin import DanelfinClient
    import datetime
    import json
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Load API key from environment variable
    danelfin_api_key = os.getenv("DANELFIN_API_KEY")
    client = DanelfinClient(api_key=danelfin_api_key)

    #today_str = event.get("today_str", datetime.date.today().strftime("%Y-%m-%d"))
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    print("Starting Ingest for Date:", today_str)

    symbols = event.get("symbols", None)
    if not symbols:
        # ToDo:  get symbols from dynDb position recs
        raise ValueError("No symbols provided in the event")

    # fetch scores for each symbol and save to JSON file
    for symbol in symbols:
        fname = f"{symbol}.ai_scores.json"
        scores = client.ranking(date=None, ticker=symbol)  # last 100 days
        if scores:
            scores_latest = scores[list(scores.keys())[0]]
            scores_latest['update_dt'] = list(scores.keys())[0]
            scores_dict = {
                "symbol": symbol,
                "ai_scores": scores_latest 
            }
            save_and_upload_json(fname, scores_dict)

        fname = f"{symbol}.trading_params.json"
        trading_params = client.trading_parameters(ticker=symbol)
        if trading_params:
            latest = list(trading_params.keys())[0]
            trading_params_latest = trading_params[latest]
            if trading_params[latest]:
                trading_params_latest['update_dt'] = latest
                trading_params_dict = {
                    "symbol": symbol,
                    "trading_params": trading_params_latest
                }
                save_and_upload_json(fname, trading_params_dict)

        ''' skipping price_forecast for now ...
        fname = f"{symbol}.price_forecast.json"
        price_forecast = client.price_forecast(ticker=symbol)
        '''

    # fetch today's top 100 scores from Danelfin API and save to JSON file
    fname = "dfin_top100.json"   
    print(f"Fetching scores for {fname}...")
    top_100 = client.ranking(date=today_str)
    save_and_upload_json(fname, top_100)

    # fetch today's Trade Ideas from Danelfin API and save to JSON file
    fname = "dfin_trade_ideas.json"   
    print(f"Fetching scores for {fname}...")
    trade_ideas = client.trade_ideas()
    save_and_upload_json(fname, trade_ideas)

    return {
        "statusCode": 200,
        "body": json.dumps("Danelfin data fetched and stored in S3 successfully!")
    }

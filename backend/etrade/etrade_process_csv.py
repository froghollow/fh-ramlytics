"""
etrade_process_csv.py  
Processes CSV files manually downloaded from E*Trade into structured JSON including account and position data, 
and uploads the JSON to S3 to be ingested into DynamoDB by the etrade_store_account Lambda function.
"""

import boto3
import os
import json
import datetime 
import pandas as pd

s3_client = boto3.client("s3", region_name="us-east-1")
s3_bucket_name = os.getenv("S3_BUCKET_NAME", "fh-danelfin-289755104220")
s3_folder = os.getenv("S3_FOLDER", "inbound/account_data")

clerk_user_id = os.getenv("CLERK_USER_ID", "user_3DM8poEbvBf5VXyVG4AGF9bdnoe") # Richard & Sue

def get_df( csv_substring ):
    from io import StringIO
    byte_content = bytes(csv_substring.encode())
    fileobj = StringIO(byte_content.decode())
    df = pd.read_csv(fileobj)

    # rename columns to replace spaces with underscores, etc.
    df.columns = df.columns.str.replace(' ', '_')
    df.columns = df.columns.str.replace('_/_', '_')
    df.columns = df.columns.str.replace('$', 'Amt')
    df.columns = df.columns.str.replace('%', 'Pct')
    df.columns = df.columns.str.replace("'", '')
    df.columns = df.columns.str.replace("'", '')
    df.columns = df.columns.str.replace('Qty_#', 'Quantity')
    df.columns = df.columns.str.replace("Portfolio", 'Account')
    return df

def export_and_upload_json(df_header, df_table, outpath=None):
    if not outpath:
        outpath = os.getenv("LOCAL_FOLDER", "/tmp/accounts")
    json_path = outpath

    json_header = json.loads(df_header.set_index('Account').to_json(orient='index'))
    json_holdings = json.loads(df_table.set_index('Symbol').to_json(orient='index'))
    json_holdings = dict(sorted(json_holdings.items()))
    #print(json.dumps(json_holdings, indent=4))
    account_id = list(json_header.keys())[0]

    # add json_account and json_holdings to a single json object
    json_account = {
        "account_id": account_id,
        "clerk_user_id": clerk_user_id,  # link to logged-in user 
        "account_name": account_id,
        "account_purpose": "",  # e.g., Literal['Long Term Growth', 'Short Term Gain', 'Retirement', 'Other']
        "record_type": "account",
        "market_dt": datetime.datetime.now().strftime("%Y-%m-%d"),
        "update_dt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  
        "symbols": list(json_holdings.keys()),
        "header": json_header,
        "holdings": json_holdings
    }

    fname = f"{account_id.replace(' ','-')}.etrade.json"
    # create directory if it doesn't exist
    os.makedirs(json_path, exist_ok=True)

    with open(f"{json_path}/{fname}", "w") as f:
        json.dump(json_account, f, indent=4)
    s3_client.upload_file(f"{json_path}/{fname}", s3_bucket_name, f"{s3_folder}/{fname}")

    print(f"Saved and uploaded {json_path}/{fname} to s3://{s3_bucket_name}/{s3_folder}/{fname}")  

    return json_account

def process_etrade_csv_downloads(inpath, outpath=None, yymmdd=None):
    df_concat_bonds = pd.DataFrame()
    df_concat_stocks = pd.DataFrame()

    if not yymmdd:
        yymmdd = datetime.datetime.now().strftime("%y%m%d")

    if not outpath:
        outpath = os.getenv("LOCAL_FOLDER", "/tmp/accounts")

    for csv_filename in os.listdir (inpath):

        if not csv_filename.startswith('PortfolioDownload') or not csv_filename.endswith('.csv'):
            continue

        #print(f"Found CSV file: {csv_filename}")

        fname = f"{inpath}/{csv_filename}"
        with open ( fname ) as f:
            data = f.read() 

        header = data[data.find('Account,'):data.find('\n\n')]
        df_header = get_df(header)
        print (f"Processing {fname}, Account {df_header['Account'][0]}")

        if "Stocks+Options" in data:
            sec_type = "Stocks+EFTs"
            table = data[data.find('Symbol,Price'):data.find('CASH,,,')]
            df_table = get_df(table)
            df_table['Account'] = df_header['Account'][0]
            #concat( df_concat_stocks, df_table)
            if df_concat_stocks.empty:
                df_concat_stocks = df_table
            else:
                df_concat_stocks = pd.concat( [df_concat_stocks, df_table] )

            # write json file for each account
            json_account = export_and_upload_json(df_header, df_table, outpath)
            
        elif "View Summary - Bonds" in data:
            sec_type = "Bonds"
            table = data[data.find('Symbol,Bond'):data.find('CASH,,,')]
            df_table = get_df(table)
            df_table['Account'] = df_header['Account'][0]
            df_table['Maturity'] = pd.to_datetime(df_table['Maturity'])
            df_table['MatMonth'] = df_table['Maturity'].dt.strftime('%b')
            #concat( df_concat_bonds, df_table)
            if df_concat_bonds.empty:
                df_concat_bonds = df_table
            else:
                df_concat_bonds = pd.concat( [df_concat_bonds, df_table] )

    df_concat_stocks.to_csv( f"{inpath}/etrade_Stocks+EFTs_{yymmdd}.csv" )
    df_concat_bonds.to_csv(  f"{inpath}/etrade_Bonds_{yymmdd}.csv" )

    return df_concat_stocks, df_concat_bonds

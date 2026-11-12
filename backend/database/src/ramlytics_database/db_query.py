from ramlytics_database import DynamoDBClient

db = DynamoDBClient()
import pandas as pd
import os
import logging
logging.basicConfig(level=logging.INFO)

from ramlytics_yfinance import yf_search

'''import dotenv
dotenv.load_dotenv()
user_id = os.getenv("CLERK_USER_ID")'''

class DbQuery:
    import dotenv
    dotenv.load_dotenv()
    #user_id = os.getenv("CLERK_USER_ID")

    def __init__(self, db_client, user_id=None):
        self.db = db_client
        if not user_id:
            user_id = os.getenv("CLERK_USER_ID")
        self.user_id = user_id
        self.get_instruments_df()
        self.get_accounts_df()

    def remove_dyndb_keycols(self, df, colnames=['PK', 'SK', 'GSI1PK', 'GSI1SK','GSI2PK', 'GSI2SK', 'GSI3PK', 'GSI3SK', 'GSI4PK', 'GSI4SK']):
        for col in df.columns:
            if col in colnames:
                df.drop(columns=[col], inplace=True)
        return df

    def get_instruments_df(self):
        self.instruments_df = self.remove_dyndb_keycols(pd.DataFrame(self.db.list_instruments()))
        return self.instruments_df

    def get_accounts_df(self):
        self.accounts_df = self.remove_dyndb_keycols(pd.DataFrame(self.db.list_accounts(self.user_id)))

        return self.accounts_df

    def get_account_positions_df(self, user_id=None, accounts=[]):
        if not user_id:
            user_id = self.user_id or os.getenv("CLERK_USER_ID")
        
        if not accounts:
            accounts = self.db.list_accounts(user_id)

        if not accounts:
            raise ValueError("User has no accounts.")
        for account in accounts:
            account_id = account["account_id"]

            # loop through positions for the current account and collect them in a list
            positions_list = []
            for position in self.db.list_positions(account_id):
                symbol = position["symbol"]
                df = self.get_instruments_df()
                current_price = df[df["symbol"] == symbol]["current_price"].iloc[0]
                avg_price_paid = position["holding"]["Price_Paid_Amt"]
                rec = {
                    "account_id": account_id,
                    "symbol": symbol,
                    "quantity": position["quantity"],
                    "avg_price_paid": avg_price_paid,
                    "current_price": current_price, 
                    "pct_gain_or_loss": round((current_price - avg_price_paid) / avg_price_paid * 100, 2) if avg_price_paid else None,
                    "total_value": position["quantity"] * current_price if position["quantity"] and current_price else None,
                }
                positions_list.append(rec)

            # convert positions_list to DataFrame and merge with positions_df
            if positions_list:
                positions_df = pd.merge(positions_df, pd.DataFrame(positions_list), how="outer") if 'positions_df' in locals() else pd.DataFrame(positions_list)    

            self.positions_df = positions_df

        return positions_df

    def get_acct_summary_by_symbol_df(self, df=None):

        if df is None:
            if not hasattr(self, 'positions_df'):
                self.get_account_positions_df()
            df = self.positions_df

        symbol_summary_df = df.groupby("symbol").agg(
            total_quantity=pd.NamedAgg(column="quantity", aggfunc="sum"),
            avg_price_paid=pd.NamedAgg(column="avg_price_paid", aggfunc="mean"),
            current_price=pd.NamedAgg(column="current_price", aggfunc="mean"),
            # list of accounts
            accounts=pd.NamedAgg(column="account_id", aggfunc=lambda x: list(set(x)))
        ).reset_index()
        symbol_summary_df['total_value'] = symbol_summary_df['total_quantity'].astype(float) * symbol_summary_df['current_price'].astype(float)
        return symbol_summary_df

    def get_positions_unique_symbols_df(self, df=None):
        if df is None:
            if not hasattr(self, 'positions_df'):
                self.get_account_positions_df()
            df = self.positions_df
        return df['symbol'].unique() if 'symbol' in df.columns else []
                   
    def get_instrument_holdings_df(self, symbols=[]):
        """ Get the 'top_10_holdings' for a list of instrument symbols """
        from decimal import Decimal

        if not symbols:
            symbols = self.instruments_df['symbol'].tolist()

        etf_holdings_df = pd.DataFrame()
        for symbol in symbols:
            #print(symbol)
            instrument = self.db.get_instrument(symbol)
            if 'top_10_holdings' not in instrument: # create a 100% placeholder for top 10 holdings             
                instrument['top_10_holdings'] = [{
                    "symbol": symbol,
                    "name": instrument.get('name', 'n/a'),
                    "weight_percent": 100,
                    "sector": instrument.get('sector', 'n/a'),
                    "industry": instrument.get('industry', 'n/a'),
                    "current_price": instrument.get('current_price', 0)
                }]
            # else: 'top_10_holdings' already exists from PDF/JSON import {name: ..., weight_percent: ...}

            holdings = instrument.pop('top_10_holdings')

            pct_in_top10 = 0
            for holding in holdings:
                eft_holding = { "etf_symbol": symbol, **holding}
                pct_in_top10 += holding.get("weight_percent", 0)

                if "symbol" in holding.keys():
                    search_result = yf_search(holding['symbol'])
                else:
                    search_result = yf_search(holding['name'])

                if search_result:
                    logging.info(search_result)
                    eft_holding['symbol'] = search_result['symbol']                        
                    eft_holding['sector'] = search_result.get('sector','n/a')
                    eft_holding['industry'] = search_result.get('industry','n/a')
                    eft_holding['current_price'] = round(Decimal(search_result.get('fastinfo',{}).get('lastPrice','0')), 2)
                    eft_holding['quote_dt'] = search_result.get('fastinfo',{}).get('quote_dt','n/a')
                else:
                    eft_holding = {
                        "etf_symbol": symbol,
                        "name": holding.get('name', 'n/a'),
                        "weight_percent": round(Decimal(holding.get('weight_percent', 0)), 2),
                        "symbol": holding.get('symbol', 'n/a'),
                        "sector": holding.get('sector', 'n/a'),
                        "industry": holding.get('industry', 'n/a'),
                        "current_price":  round(Decimal(instrument.get('fastinfo',{}).get('lastPrice',0.01)), 2)
                    }
                
                etf_holdings_df = pd.concat([etf_holdings_df, pd.DataFrame([eft_holding])], ignore_index=True)

            logging.info(f"Symbol: {symbol}, Pct in Top 10: {pct_in_top10}")
            outside_top_10_weight = 100 - pct_in_top10
            if outside_top_10_weight > 0:
                outside_top_10 = {
                    "etf_symbol": symbol,
                    "symbol": symbol,
                    "name": "holdings in addition to top 10",
                    "weight_percent": outside_top_10_weight,
                    "current_price": instrument.get("current_price", None),
                    "quoteType": "EFT",
                    "industry": '--',
                    "sector": '--',
                }
                etf_holdings_df = pd.concat([etf_holdings_df, pd.DataFrame([outside_top_10])], ignore_index=True)

            etf_holdings_df = etf_holdings_df[['etf_symbol', 'name', 'weight_percent', 'symbol', 'sector', 'industry', 'current_price', 'quote_dt']]
            etf_holdings_df['eft_price_pct'] = etf_holdings_df['weight_percent'] * etf_holdings_df['current_price'] / 100
            logging.info(f"Processed {symbol}")

        return etf_holdings_df

    def get_position_holdings(self, df_holdings, df_positions):
        """ join holdings and accounts where etf_symbol matches the symbol in accounts """
        df_position_holdings = pd.merge(df_holdings, df_positions, left_on="etf_symbol", right_on="symbol", how="inner")
        df_position_holdings = df_position_holdings[['account_id', 'etf_symbol', 'name', 'weight_percent', 'symbol_x', 'sector', 'industry', 'quote_dt', 'total_value' ]]
        # ToDo:df_position_holdings[['account_id', 'etf_symbol', 'name', 'symbol_x', 'sector', 'industry', 'quote_dt', 'price', 'shares', 'total_value', 'weight_percent', 'holding_value']]
        df_position_holdings = df_position_holdings.rename(columns={"symbol_x": "symbol"})

        df_position_holdings['holding_value'] = round(df_position_holdings['total_value'].astype(float) * (df_position_holdings['weight_percent'] / 100).astype(float), 2)
        df_position_holdings['name'] = df_position_holdings['name'].str.upper()
        df_position_holdings['name'] = df_position_holdings['name'].str.replace(r'[^A-Z0-9 ]', '', regex=True)
        df_position_holdings.fillna('n/a', inplace=True)

        return df_position_holdings

    def get_eft_holdings_by_secname(self, df_position_holdings):
        """ holdings grouped by security name and symbol with lists of associated accounts and ETFs """
        df_eft_holdings_by_secname = df_position_holdings.groupby(["name", "symbol"]).agg(
            total_holding_value=pd.NamedAgg(column="holding_value", aggfunc="sum"),
            account_list=pd.NamedAgg(column="account_id", aggfunc=lambda x: list(set(x))),
            etf_list=pd.NamedAgg(column="etf_symbol", aggfunc=lambda x: list(set(x)))
        ).reset_index()

        total_portfolio_value = round(df_eft_holdings_by_secname["total_holding_value"].sum(), 2)
        df_eft_holdings_by_secname["total_holding_value"] = round(df_eft_holdings_by_secname["total_holding_value"].astype(float), 2)
        df_eft_holdings_by_secname["weight_percent"] = round(df_eft_holdings_by_secname["total_holding_value"] / total_portfolio_value * 100, 2)

        return df_eft_holdings_by_secname


    def get_instrument_scores_df(self, symbols=[]):
        if not symbols:
            symbols = self.instruments_df['symbol'].tolist()

        scores_df = pd.DataFrame()
        for symbol in symbols:
            #print(symbol)
            instrument = self.db.get_instrument(symbol)
            if 'ai_scores' in instrument:
                ai_scores = instrument.pop('ai_scores')
                trading_params = instrument.pop('trading_params', {})

                inst = { 
                    "symbol": symbol, 
                    "current_price": instrument.get("current_price"),
                    **ai_scores, 
                    **trading_params }

                scores_df = pd.concat([scores_df, pd.DataFrame([inst])], ignore_index=True)
                # reorder columns
                scores_df = scores_df[['symbol', 'current_price', 'signal', 'aiscore', 'fundamental', 'low_risk', 'sentiment', 'technical', 
                    'entry_price', 'stop_loss', 'stop_loss_pct', 'take_profit', 'take_profit_pct',        
                    'currency', 'horizon', 'update_dt']]

        return scores_df

    def get_account_total_equities_df(self, positions_df=None):
        '''Summarize total_value of positions_df by account_id. Returns a DataFrame with account_id and total_equities_value.'''
        if positions_df is None:
            positions_df = self.get_account_positions_df()  # Assuming there's a method to get positions_df if not provided

        account_total_equities_df = positions_df.groupby("account_id")["total_value"].sum().reset_index()
        account_total_equities_df.rename(columns={"total_value": "total_equities_value"}, inplace=True)
        return account_total_equities_df

    def get_account_headers_df(self):
        '''Get a DataFrame summarizing account headers, including total equities and bonds values.'''
        account_headers = []
        # for each row in the account_headers dataframe
        for index, row in self.accounts_df.iterrows():
            account_id = row['account_id']
            account_header = row['header'][account_id]
            account_header["account_id"] = account_id

            account_total_equities_df = self.get_account_total_equities_df()

            account_header["total_equities_value"] = account_total_equities_df.loc[account_total_equities_df["account_id"] == account_id, "total_equities_value"].values[0]
            account_header["total_bonds_value"] = account_header['Net_Account_Value'] - account_header["total_equities_value"]
            # ToDo: Calculate Gain columns based on Postions data

            # select and rearrange the columns in the desired order
            account_header = {key: account_header[key] for key in [
                'account_id',
                'total_equities_value',
                'total_bonds_value',
                'Net_Account_Value',
                'Total_Gain_Pct',       
                'Total_Gain_Amt',
                'Cash_Purchasing_Power',
                'Days_Gain_Unrealized_Pct',
                'Days_Gain_Unrealized_Amt'
            ]}

            account_headers.append({
                **account_header
            })

        # account_headers list into account_headers_df
        account_headers_df = pd.DataFrame(account_headers)

        return account_headers_df

    def get_instrument_market_summary_df(self, symbols=[]):
        if not symbols:
            symbols = self.instruments_df['symbol'].tolist()

        marketdata_df = pd.DataFrame()
        for symbol in symbols:
            #print(symbol)
            instrument = self.db.get_instrument(symbol)
            if 'fastinfo' in instrument:
                fastinfo = instrument.pop('fastinfo')

                inst = { 
                    "symbol": symbol, 
                    "current_price": instrument.get("current_price"),
                    **fastinfo }

                marketdata_df = pd.concat([marketdata_df, pd.DataFrame([inst])], ignore_index=True)

        # rename columns
        marketdata_df.rename(columns={
            'symbol': 'symbol',
            'current_price': 'current_price',
            'currency': 'currency',
            'timezone': 'timezone',
            'threeMonthAverageVolume': 'vol_avg_3m',
            'lastVolume': 'vol_last',
            'open': 'open',
            'quoteType': 'quote_type',
            'twoHundredDayAverage': 'price_avg_200d',
            'dayHigh': 'day_high',
            'marketCap': 'market_cap',
            'dayLow': 'day_low',
            'yearChange': 'year_change',
            'quote_dt': 'quote_dt',
            'fiftyDayAverage': 'price_avg_50d',
            'shares': 'shares',
            'exchange': 'exchange',
            'lastPrice': 'price_last',
            'yearHigh': 'year_high',
            'tenDayAverageVolume': 'vol_avg_10d',
            'previousClose': 'close_previous',
            'regularMarketPreviousClose': 'close_previous_reg_mkt',
            'yearLow': 'year_low'}, inplace=True)
        
        # calculate relative volumes
        marketdata_df['vol_relative_3m'] = marketdata_df['vol_last'] / marketdata_df['vol_avg_3m']
        marketdata_df['vol_relative_10d'] = marketdata_df['vol_last'] / marketdata_df['vol_avg_10d']

        # rearrange columns in alphabetical order with "symbol" first
        marketdata_df = marketdata_df[['symbol'] + sorted([col for col in list(marketdata_df.columns) if col != 'symbol'])]

        return marketdata_df

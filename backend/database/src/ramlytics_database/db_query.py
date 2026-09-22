from ramlytics_database import DynamoDBClient

db = DynamoDBClient()
import pandas as pd
import os
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
        self.set_instruments_df()
        self.set_accounts_df()

    def remove_dyndb_keycols(self, df, colnames=['PK', 'SK', 'GSI1PK', 'GSI1SK','GSI2PK', 'GSI2SK', 'GSI3PK', 'GSI3SK', 'GSI4PK', 'GSI4SK']):
        for col in df.columns:
            if col in colnames:
                df.drop(columns=[col], inplace=True)
        return df

    def set_instruments_df(self):
        self.instruments_df = self.remove_dyndb_keycols(pd.DataFrame(self.db.list_instruments()))
        return self.instruments_df

    def set_accounts_df(self):
        self.accounts_df = self.remove_dyndb_keycols(pd.DataFrame(self.db.list_accounts(self.user_id)))

        return self.accounts_df

    def get_account_positions(self, user_id=None):
        if not user_id:
            user_id = self.user_id or os.getenv("CLERK_USER_ID")
        
        accounts = self.db.list_accounts(user_id)

        if not accounts:
            raise ValueError("User has no accounts.")
        for account in accounts:
            account_id = account["account_id"]

            # loop through positions for the current account and collect them in a list
            positions_list = []
            for position in self.db.list_positions(account_id):
                symbol = position["symbol"]
                current_price = self.instruments_df[self.instruments_df["symbol"] == symbol]["current_price"].iloc[0]
                rec = {
                    "account_id": account_id,
                    "symbol": symbol,
                    "quantity": position["quantity"],
                    "avg_price_paid": position["holding"]["Price_Paid_Amt"],
                    "current_price": current_price, 
                }
                positions_list.append(rec)

            # convert positions_list to DataFrame and merge with positions_df
            if positions_list:
                positions_df = pd.merge(positions_df, pd.DataFrame(positions_list), how="outer") if 'positions_df' in locals() else pd.DataFrame(positions_list)    

            self.positions_df = positions_df

        return positions_df

    def summarize_accounts_by_symbol(self, df=None):
        if df is None:
            if not hasattr(self, 'positions_df'):
                self.get_account_positions()
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

    def get_positions_unique_symbols(self, df=None):
        if df is None:
            if not hasattr(self, 'positions_df'):
                self.get_account_positions()
            df = self.positions_df
        return df['symbol'].unique() if 'symbol' in df.columns else []

    def enhance_top10_holdings(self, symbols=[]):
        # ToDo: move enhance_top10_holdings to DynamoDBClient
        if not symbols:
            symbols = self.get_positions_unique_symbols()

        for symbol in symbols:
            #top_10_holdings = 
            instrument = self.db.get_instrument(symbol)

            top_10_holdings = instrument.get("top_10_holdings", None)
            if not top_10_holdings:
                top_10_holdings = [
                    {
                        "symbol" : symbol,
                        "weight_percent" : 100
                    }
                ]

            pct_in_top10 = 0
            for holding in top_10_holdings:
                pct_in_top10 += holding.get("weight_percent", 0)

                search_key = holding.get("symbol", holding.get("name"))
                search_result = yf_search(search_key)
                if not search_result:
                    search_result = yf_search(symbol)

                # merge subholding data into the holding
                if search_result:
                    holding.update(search_result)

            # if pct_in_top10 <> 100, it means there are holdings outside the top 10
            print(f"Symbol: {symbol}, Pct in Top 10: {pct_in_top10}")

            # replace list item 'holdings outside the top 10' if it already exists
            top_10_holdings = [h for h in top_10_holdings if h.get("name") != "holdings outside the top 10"]
            outside_top_10_weight = 100 - pct_in_top10
            if outside_top_10_weight > 0:
                top_10_holdings.append({
                    "symbol": symbol,
                    "name": "holdings outside the top 10",
                    "weight_percent": outside_top_10_weight,
                    "current_price": instrument.get("current_price", None),
                    "quoteType": "EFT",
                    "industry": '--',
                    "sector": '--',
                })

            #instrument["top_10_holdings"] = top_10_holdings
            self.db.put_instrument(symbol, **{"top_10_holdings": top_10_holdings}) 
                   
    def get_instrument_holdings(self, symbols=[]):
        if not symbols:
            symbols = self.instruments_df['symbol'].tolist()

        eft_holdings_df = pd.DataFrame()
        for symbol in symbols:
            print(symbol)
            instrument = self.db.get_instrument(symbol)
            if 'top_10_holdings' in instrument:
                inst = { "symbol": symbol }
                holdings = instrument.pop('top_10_holdings')
                # create a combined dictionary of the instrument symbol and its top 10 holdings
                #instrument_top_10_holdings = { "symbol": symbol, **holdings }
                for holding in holdings:
                    if "symbol" in holding.keys():
                        #eft_holding = { "etf_symbol": symbol, "holding_symbol": holding['symbol'] }
                        eft_holding = { "etf_symbol": symbol, **holding}
                        #print(eft_holding)
                        eft_holdings_df = pd.concat([eft_holdings_df, pd.DataFrame([eft_holding])], ignore_index=True)

        return eft_holdings_df

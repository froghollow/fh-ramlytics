"""
yf_tickers.py
Yahoo Finance ticker utilities.
Provides functions to check if the market is open, search for tickers, and download historical and intraday data.
"""
import pandas as pd
import datetime as dt

def market_is_open():
    import pytz
    import holidays

    eastern = pytz.timezone('US/Eastern')
    now = dt.datetime.now(eastern)
    
    # Market hours: 9:30 AM to 4:00 PM Eastern, Monday to Friday
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    # Check if today is a weekday
    is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4

    # Check if today is a US holiday
    us_holidays = holidays.US(years=now.year)
    is_holiday = now.date() in us_holidays

    # Final check
    is_open = is_weekday and not is_holiday and market_open <= now <= market_close
    return is_open

def yf_search(query: str):
    ''' Looks up symbol or fuzzy name on Yahoo Finance and returns the first matching quote. 
        If no exact match is found, returns the first quote from the search results. '''
    import yfinance as yf

    lookup = yf.Search(query)
    
    for quote in lookup.response.get("quotes", []):
        if quote['symbol'] == query or quote['shortname'] == query or quote['longname'] == query:
            return quote
        else:
            print(f"No exact symbol or name match for '{query}'.  Returning first quote instead.")
            return lookup.response.get("quotes", [])[0]

class Tickers():

    def __init__(self, symbols, filepath=None, start_dt=None, end_dt=None ):
        if end_dt is None:
            end_dt = dt.datetime.now().strftime("%Y-%m-%d")

        self.symbols = symbols
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.df_tickers_hist = pd.DataFrame()
        self.df_tickers_today = pd.DataFrame()
        self.df_dict = {}
        if filepath is not None:
            self.read_tickers_from_xlsx(filepath)
        else:
            self.download_tickers_hist(symbols, start_dt, end_dt)
    
    def download_tickers_hist(self, symbols=[], start_dt=None, end_dt=None):
        """
        Bulk download of historical data for multiple symbols
        """
        import yfinance as yf

        if symbols == []:
            symbols = self.symbols.copy()
            symbols.remove('CASH')

        if end_dt is None:
            end_dt = dt.datetime.now().strftime("%Y-%m-%d")

        # bulk download of historical data for multiple symbols
        df_hist = yf.download(symbols, start=start_dt, end=end_dt) # set auto_adjust=True to get adjusted close prices?
        df_hist = df_hist.swaplevel(axis="columns").sort_index(axis="columns")

        if market_is_open():
            # If market is open, we append only the last txn of today's data
            if self.df_tickers_today.empty:
                self.download_tickers_today(symbols)

            df_lasttick = self.df_tickers_today.iloc[-1:].copy()
            df_lasttick.index = df_lasttick.index.tz_localize(None)  # Remove timezone info if present
            df_hist = pd.concat([df_hist, df_lasttick], axis=0 )
        
        self.df_tickers_hist = df_hist

    def download_tickers_today(self, symbols=[], interval='5m'):
        """
        Bulk download of today's data for multiple symbols
        """
        import yfinance as yf

        if symbols == []:
            symbols = self.symbols.copy()
            symbols.remove('CASH')

        if not market_is_open():
            print("NOTE:  Market is closed. Download will comprise last trading day.")

        # bulk download of 1 day's data for multiple symbols
        df_today = yf.download(symbols, period='1d', interval=interval)
        #df_today = df_today.fillna(0)
        df_today = df_today.swaplevel(axis="columns").sort_index(axis="columns")
        df_today = df_today.drop(columns=['Adj Close'], level=1, errors='ignore')
        
        self.df_tickers_today = df_today

    def download_company_info(self, symbol):
        """
        Download metadata and financial info (Income statement, Balance Sheet, Cash Flow) for a specific symbol.
        """
        # Income statement, balance sheet, cash flows
        import yfinance as yf
        import pandas as pd

        # Load ticker
        ticker = yf.Ticker(symbol)
        metadata_dict = ticker.info

        # Retrieve financials
        annual = ticker.financials
        quarterly = ticker.quarterly_financials

        # Combine them side by side
        df_merged_financials = pd.concat([annual, quarterly], axis=1)

        # Optional: Rename columns for clarity
        df_merged_financials.columns = [f"Ann_{col.date()}" for col in annual.columns] + [f"Qtr_{col.date()}" for col in quarterly.columns]

        return metadata_dict, df_merged_financials

    def get_tickers(self, symbol, df_tickers=None):
        """
        Get data for a specific ticker.
        """
        if df_tickers is None:
            df_tickers = self.df_tickers_hist

        if symbol in self.symbols:
            df = df_tickers[symbol].copy()
            df['Symbol'] = symbol
            return df
        else:
            print(f"Ticker {symbol} not found.")
            return None

    def get_latest_ticker(self, symbol, df_tickers=None):
        """
        Get the latest (last)row of data for a specific ticker as a dictionary.
        """
        df = self.get_tickers(symbol, df_tickers=df_tickers)
        if df is not None:
            latest = df.tail(1).to_dict(orient="records")[0]
            latest["DateTime"] = df.tail(1).index[0].isoformat(sep=' ')
            return latest



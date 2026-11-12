"""
bollinger.py
Compute Bollinger Bands for multiple tickers and detect 'squeeze' events
where band width contracts to the narrowest level within a rolling period.

Author: Richard Myers
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


# ---------------------------------------------------------
# Bollinger Band Calculation
# ---------------------------------------------------------

def compute_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    num_std: float = 2.0
) -> pd.DataFrame:
    """
    Compute Bollinger Bands for a single ticker OHLC dataframe.

    Required columns: ['open','high','low','close']

    Returns the original dataframe with:
        - sma
        - upper_band
        - lower_band
        - band_width
    """

    close = df["close"]

    sma = close.rolling(period).mean()
    std = close.rolling(period).std()

    upper = sma + num_std * std
    lower = sma - num_std * std
    width = upper - lower

    out = df.copy()
    out["sma"] = sma
    out["upper_band"] = upper
    out["lower_band"] = lower
    out["band_width"] = width

    return out


# ---------------------------------------------------------
# Squeeze Detection
# ---------------------------------------------------------

def detect_squeeze(
    df: pd.DataFrame,
    lookback: int = 100
) -> pd.DataFrame:
    """
    Detect squeeze events where the band width is the narrowest
    within the rolling lookback window.

    Adds:
        - min_band_width
        - squeeze (bool)
    """

    df = df.copy()
    df["min_band_width"] = df["band_width"].rolling(lookback).min()
    df["squeeze"] = df["band_width"] <= df["min_band_width"]

    return df


# ---------------------------------------------------------
# Multi‑Ticker Pipeline
# ---------------------------------------------------------

def process_tickers(
    ohlc_map: Dict[str, pd.DataFrame],
    period: int = 20,
    num_std: float = 2.0,
    squeeze_lookback: int = 100
) -> Dict[str, pd.DataFrame]:
    """
    Compute Bollinger Bands + squeeze detection for a dictionary
    of ticker → OHLC dataframe.

    Returns:
        dict[ticker] = enriched dataframe
    """

    results = {}

    for ticker, df in ohlc_map.items():
        bb = compute_bollinger_bands(df, period, num_std)
        sq = detect_squeeze(bb, squeeze_lookback)
        results[ticker] = sq

    return results


# ---------------------------------------------------------
# Squeeze Alert Extraction
# ---------------------------------------------------------

def squeeze_alerts(
    processed_map: Dict[str, pd.DataFrame]
) -> Dict[str, pd.DataFrame]:
    """
    Extract rows where squeeze == True for each ticker.

    Returns:
        dict[ticker] = dataframe of squeeze rows
    """

    alerts = {}

    for ticker, df in processed_map.items():
        sq = df[df["squeeze"] == True]
        if not sq.empty:
            alerts[ticker] = sq

    return alerts


# ---------------------------------------------------------
# Example Usage (remove if embedding in production)
# ---------------------------------------------------------

if __name__ == "__main__":
    # Example dummy data
    dates = pd.date_range("2024-01-01", periods=200)
    dummy = pd.DataFrame({
        "open": np.random.rand(200) * 100,
        "high": np.random.rand(200) * 100,
        "low": np.random.rand(200) * 100,
        "close": np.random.rand(200) * 100,
    }, index=dates)

    tickers = {"AAPL": dummy, "MSFT": dummy.copy()}

    processed = process_tickers(tickers)
    alerts = squeeze_alerts(processed)

    for t, df in alerts.items():
        print(f"\nSQUEEZE ALERTS FOR {t}")
        print(df.tail())

"""
Step 1: Data Collection
Downloads OHLCV data for TICKER and BENCHMARK.
- Daily data: yfinance (full history)
- Intraday 5-min data: Alpaca API (full history, requires API keys)
"""
import sys
from pathlib import Path

# Add parent to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add shared to path for Alpaca client
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import (
    TICKER, BENCHMARK, START_DATE, END_DATE,
    DATA_RAW, DATA_PROC
)


def download_daily_data(ticker: str, start: str, end: str | None) -> pd.DataFrame:
    """Download daily OHLCV data for a ticker."""
    print(f"📥 Downloading daily data for {ticker}...")
    
    end_date = end or datetime.now().strftime("%Y-%m-%d")
    
    df = yf.download(ticker, start=start, end=end_date, interval="1d", progress=False)
    
    if df.empty:
        print(f"  ⚠️ No data returned for {ticker}")
        return pd.DataFrame()
    
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Reset index to make Date a column
    df = df.reset_index()
    df.rename(columns={"index": "Date"}, inplace=True)
    if "Date" not in df.columns and "Datetime" in df.columns:
        df.rename(columns={"Datetime": "Date"}, inplace=True)
    
    # Clean: drop rows with NaN or 0 close
    df = df[df["Close"].notna() & (df["Close"] > 0)]
    
    print(f"  ✅ {ticker} daily: {len(df)} rows, {df['Date'].min()} to {df['Date'].max()}")
    return df


def download_intraday_data_alpaca(ticker: str, start: str, end: str | None) -> pd.DataFrame:
    """
    Download 5-minute intraday data using Alpaca API.
    Unlike yfinance, Alpaca provides full historical intraday data.
    
    Uses Alpaca paper account keys (which have market data access).
    """
    print(f"📥 Downloading 5-min intraday data for {ticker} via Alpaca...")
    
    import os
    import requests
    
    # Load paper API keys (paper keys have market data access)
    from shared.config import env_loader
    env_loader.load_keys('paper', override=True)
    
    # Get API credentials from environment
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("Alpaca API keys not found. Check shared/config/keys/paper.env")
    
    data_url = 'https://data.alpaca.markets'
    headers = {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
    }
    
    end_date = end or datetime.now().strftime("%Y-%m-%d")
    
    # Alpaca limits bars per request, so we need to paginate
    # We'll collect in chunks of ~10,000 bars (about 3 weeks of 5-min data)
    all_bars = []
    current_start = start
    page_token = None
    max_iterations = 200  # Safety limit
    iteration = 0
    
    print(f"  Fetching from {start} to {end_date}...")
    
    while iteration < max_iterations:
        iteration += 1
        
        # Build request
        url = f"{data_url}/v2/stocks/{ticker}/bars"
        params = {
            'timeframe': '5Min',
            'start': current_start,
            'end': end_date,
            'limit': 10000,
            'feed': 'iex',  # Use IEX for free market data
            'adjustment': 'split'  # Adjust for splits
        }
        if page_token:
            params['page_token'] = page_token
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"  ⚠️ Alpaca API error: {response.status_code}")
            print(f"     {response.text[:200]}")
            break
        
        data = response.json()
        bars = data.get('bars', [])
        
        if not bars:
            break
        
        all_bars.extend(bars)
        
        # Check for pagination
        page_token = data.get('next_page_token')
        if not page_token:
            break
        
        # Progress indicator
        if iteration % 10 == 0:
            print(f"     ...fetched {len(all_bars)} bars so far...")
    
    if not all_bars:
        print(f"  ⚠️ No intraday data returned for {ticker}")
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(all_bars)
    
    # Rename columns to match expected format
    df.rename(columns={
        't': 'datetime',
        'o': 'Open',
        'h': 'High',
        'l': 'Low',
        'c': 'Close',
        'v': 'Volume',
        'vw': 'VWAP',
        'n': 'NumTrades'
    }, inplace=True)
    
    # Parse datetime
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    # Convert to US/Eastern and strip timezone for consistency
    if df['datetime'].dt.tz is not None:
        df['datetime'] = df['datetime'].dt.tz_convert('US/Eastern').dt.tz_localize(None)
    else:
        # Alpaca returns UTC, convert to Eastern
        df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize('UTC').dt.tz_convert('US/Eastern').dt.tz_localize(None)
    
    # Extract date for grouping
    df['date'] = df['datetime'].dt.date
    
    # Clean: drop rows with NaN or 0 close
    df = df[df['Close'].notna() & (df['Close'] > 0)]
    
    # Sort by datetime
    df = df.sort_values('datetime').reset_index(drop=True)
    
    print(f"  ✅ {ticker} 5-min: {len(df)} rows, {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"     Unique trading days: {df['date'].nunique()}")
    
    return df


def download_intraday_data_yfinance(ticker: str) -> pd.DataFrame:
    """
    Download 5-minute intraday data.
    yfinance limits to ~60 days for 5-min data, so we get what's available.
    """
    print(f"📥 Downloading 5-min intraday data for {ticker}...")
    
    # yfinance 5-min data: max period is 60 days
    df = yf.download(ticker, period="60d", interval="5m", progress=False)
    
    if df.empty:
        print(f"  ⚠️ No intraday data returned for {ticker}")
        return pd.DataFrame()
    
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Reset index
    df = df.reset_index()
    if "Datetime" in df.columns:
        df.rename(columns={"Datetime": "datetime"}, inplace=True)
    elif "index" in df.columns:
        df.rename(columns={"index": "datetime"}, inplace=True)
    
    # Convert to US/Eastern and strip timezone for consistency
    if df["datetime"].dt.tz is not None:
        df["datetime"] = df["datetime"].dt.tz_convert("US/Eastern").dt.tz_localize(None)
    
    # Extract date for grouping
    df["date"] = df["datetime"].dt.date
    
    # Clean: drop rows with NaN or 0 close
    df = df[df["Close"].notna() & (df["Close"] > 0)]
    
    # Sort by datetime
    df = df.sort_values("datetime").reset_index(drop=True)
    
    print(f"  ✅ {ticker} 5-min: {len(df)} rows, {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"     Unique trading days: {df['date'].nunique()}")
    
    return df


def main():
    print("=" * 60)
    print("STEP 1: DATA COLLECTION")
    print("=" * 60)
    print(f"Target Ticker: {TICKER}")
    print(f"Benchmark: {BENCHMARK}")
    print(f"Date Range: {START_DATE} to {END_DATE or 'today'}")
    print()
    
    # Ensure directories exist
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    
    # Download daily data for TICKER
    df_ticker_daily = download_daily_data(TICKER, START_DATE, END_DATE)
    if not df_ticker_daily.empty:
        path = DATA_RAW / f"{TICKER}_daily.csv"
        df_ticker_daily.to_csv(path, index=False)
        print(f"  💾 Saved to {path}")
    
    # Download daily data for BENCHMARK
    df_bench_daily = download_daily_data(BENCHMARK, START_DATE, END_DATE)
    if not df_bench_daily.empty:
        path = DATA_RAW / f"{BENCHMARK}_daily.csv"
        df_bench_daily.to_csv(path, index=False)
        print(f"  💾 Saved to {path}")
    
    # Download intraday data for TICKER using Alpaca (full history)
    # Fallback to yfinance if Alpaca fails
    try:
        df_ticker_5min = download_intraday_data_alpaca(TICKER, START_DATE, END_DATE)
    except Exception as e:
        print(f"  ⚠️ Alpaca failed: {e}")
        print(f"  Falling back to yfinance (limited to 60 days)...")
        df_ticker_5min = download_intraday_data_yfinance(TICKER)
    
    if not df_ticker_5min.empty:
        path = DATA_RAW / f"{TICKER}_5min.csv"
        df_ticker_5min.to_csv(path, index=False)
        print(f"  💾 Saved to {path}")
    
    print()
    print("=" * 60)
    print("DATA COLLECTION COMPLETE")
    print("=" * 60)
    
    # Summary
    print("\n📊 Summary:")
    if not df_ticker_daily.empty:
        print(f"  {TICKER} daily: {len(df_ticker_daily)} rows")
    if not df_bench_daily.empty:
        print(f"  {BENCHMARK} daily: {len(df_bench_daily)} rows")
    if not df_ticker_5min.empty:
        print(f"  {TICKER} 5-min: {len(df_ticker_5min)} rows ({df_ticker_5min['date'].nunique()} days)")
    
    # Check for any issues
    if df_ticker_daily.empty or df_bench_daily.empty:
        print("\n⚠️ WARNING: Missing daily data. RS(Z) calculation may fail.")
    if df_ticker_5min.empty:
        print("\n⚠️ WARNING: Missing intraday data. Intraday slope detection will be limited.")


if __name__ == "__main__":
    main()

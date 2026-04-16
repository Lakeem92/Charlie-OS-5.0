"""
Regime Composite Score — Data Collection
Fetches equity prices (Alpaca) and FRED macro series, merges into
a single daily DataFrame aligned to the equity trading calendar.
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
from pathlib import Path
from datetime import datetime

from shared.data_router import DataRouter
from shared.config.api_clients import FREDClient

# ── Paths ─────────────────────────────────────────────────────────
STUDY_DIR = Path(__file__).resolve().parent
DATA_DIR = STUDY_DIR / 'outputs' / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Config ────────────────────────────────────────────────────────
START_DATE = '2016-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

EQUITY_TICKERS = ['XLY', 'XLP', 'SPY', 'QQQ', 'IWM']
FRED_SERIES = {
    'vix': 'VIXCLS',
    'hy_spread': 'BAMLH0A0HYM2',
    'yield_curve': 'T10Y2Y',
}


def collect_equity_prices() -> pd.DataFrame:
    """Pull daily closes for all equity tickers via DataRouter.
    Uses yfinance for ETF macro proxies — Alpaca IEX only goes back ~5yr,
    but this study requires 10yr (2016+) for proper z-score warmup.
    These are ETFs used as macro regime indicators, not individual equity studies."""
    frames = {}
    for ticker in EQUITY_TICKERS:
        print(f"  Fetching {ticker}...")
        df = DataRouter.get_price_data(
            ticker=ticker,
            start_date=START_DATE,
            end_date=END_DATE,
            timeframe='daily',
            source='yfinance',
        )
        # Normalize index to date only (strip timezone)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        frames[ticker] = df['Close']

    prices = pd.DataFrame(frames)
    prices.index.name = 'date'
    prices = prices.sort_index()
    print(f"  Equity prices: {len(prices)} rows, {prices.columns.tolist()}")
    return prices


def collect_fred_series() -> pd.DataFrame:
    """Pull FRED macro series via FREDClient (fredapi)."""
    client = FREDClient()
    frames = {}
    for label, series_id in FRED_SERIES.items():
        print(f"  Fetching FRED {series_id} ({label})...")
        s = client.get_series(series_id, start_date=START_DATE, end_date=END_DATE)
        s.index = pd.to_datetime(s.index).normalize()
        s.name = label
        frames[label] = s

    macro = pd.DataFrame(frames)
    macro.index.name = 'date'
    macro = macro.sort_index()
    print(f"  FRED series: {len(macro)} rows, {macro.columns.tolist()}")
    return macro


def merge_and_save(prices: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """
    Merge equity closes with FRED macro data.
    Forward-fill FRED gaps, then inner-join on equity trading calendar.
    """
    # Forward-fill FRED so weekends/holidays carry last value
    macro = macro.ffill()

    # Inner join on equity dates (trading days only)
    merged = prices.join(macro, how='inner')

    # Drop any rows where equity data is missing
    merged = merged.dropna(subset=EQUITY_TICKERS)

    print(f"  Merged dataset: {len(merged)} rows")
    print(f"  Date range: {merged.index.min().date()} → {merged.index.max().date()}")
    print(f"  NaN summary:\n{merged.isna().sum()}")

    save_path = DATA_DIR / 'raw_merged.csv'
    merged.to_csv(save_path)
    print(f"  Saved → {save_path}")
    return merged


def main():
    print("=" * 60)
    print("REGIME COMPOSITE SCORE — DATA COLLECTION")
    print("=" * 60)
    print(f"Period: {START_DATE} → {END_DATE}")
    print()

    print("[1/3] Collecting equity prices...")
    prices = collect_equity_prices()

    print("[2/3] Collecting FRED macro series...")
    macro = collect_fred_series()

    print("[3/3] Merging and saving...")
    merged = merge_and_save(prices, macro)

    print()
    print("DATA COLLECTION COMPLETE")
    print(f"  Rows: {len(merged)}")
    print(f"  Columns: {merged.columns.tolist()}")
    return merged


if __name__ == '__main__':
    main()

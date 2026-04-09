"""
WATCHLIST HELPER — Canonical access to Lakeem's master watchlist.
Usage:
    from shared.watchlist import get_watchlist
    tickers = get_watchlist()
"""

import pandas as pd
from pathlib import Path

WATCHLIST_PATH = Path(r'C:\QuantLab\Data_Lab\shared\config\watchlist.csv')


def get_watchlist() -> list:
    """Return the master watchlist as a list of ticker strings."""
    if not WATCHLIST_PATH.exists():
        raise FileNotFoundError(
            f"Watchlist not found at {WATCHLIST_PATH}. "
            "Run the watchlist ingestion script first."
        )
    df = pd.read_csv(WATCHLIST_PATH)
    return df['Symbol'].tolist()


def get_watchlist_df() -> pd.DataFrame:
    """Return the master watchlist as a DataFrame."""
    if not WATCHLIST_PATH.exists():
        raise FileNotFoundError(
            f"Watchlist not found at {WATCHLIST_PATH}. "
            "Run the watchlist ingestion script first."
        )
    return pd.read_csv(WATCHLIST_PATH)


def ticker_in_watchlist(ticker: str) -> bool:
    """Check if a ticker is in the master watchlist."""
    return ticker.upper() in get_watchlist()


def get_watchlist_count() -> int:
    """Return the number of tickers in the watchlist."""
    return len(get_watchlist())

"""
WATCHLIST HELPER — Canonical access to Lakeem's ticker universes.
Usage:
    from shared.watchlist import get_watchlist, get_focus_list
    master = get_watchlist()
    focus = get_focus_list()
"""

import pandas as pd
from pathlib import Path

ROOT = Path(r'C:\QuantLab\Data_Lab')
WATCHLIST_PATH = ROOT / 'shared' / 'config' / 'watchlist.csv'
FOCUS_LIST_PATH = ROOT / 'watchlists' / 'focus_list.csv'


def _read_list(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found at {path}. "
            "Create or refresh the CSV first."
        )

    df = pd.read_csv(path)
    if 'Symbol' not in df.columns and 'ticker' not in df.columns:
        raise ValueError(f"{label} must contain a 'Symbol' or 'ticker' column: {path}")

    if 'Symbol' not in df.columns and 'ticker' in df.columns:
        df = df.rename(columns={'ticker': 'Symbol'})

    cleaned = df.copy()
    cleaned['Symbol'] = cleaned['Symbol'].astype(str).str.strip().str.upper()
    cleaned = cleaned[cleaned['Symbol'] != '']
    cleaned = cleaned.drop_duplicates(subset=['Symbol']).reset_index(drop=True)
    return cleaned


def get_watchlist() -> list:
    """Return the master watchlist as a list of ticker strings."""
    return _read_list(WATCHLIST_PATH, 'Watchlist')['Symbol'].tolist()


def get_watchlist_df() -> pd.DataFrame:
    """Return the master watchlist as a DataFrame."""
    return _read_list(WATCHLIST_PATH, 'Watchlist')


def ticker_in_watchlist(ticker: str) -> bool:
    """Check if a ticker is in the master watchlist."""
    return ticker.upper() in get_watchlist()


def get_watchlist_count() -> int:
    """Return the number of tickers in the master watchlist."""
    return len(get_watchlist())


def get_focus_list() -> list:
    """Return the focus list as a list of ticker strings."""
    return _read_list(FOCUS_LIST_PATH, 'Focus list')['Symbol'].tolist()


def get_focus_list_df() -> pd.DataFrame:
    """Return the focus list as a DataFrame."""
    return _read_list(FOCUS_LIST_PATH, 'Focus list')


def ticker_in_focus_list(ticker: str) -> bool:
    """Check if a ticker is in the focus list."""
    return ticker.upper() in get_focus_list()


def get_focus_list_count() -> int:
    """Return the number of tickers in the focus list."""
    return len(get_focus_list())

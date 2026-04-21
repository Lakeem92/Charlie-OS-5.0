"""
Shared utilities for all QuantLab data collectors.
Provides standard JSON output, error handling, and argument parsing.
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import json
import argparse
import traceback
from pathlib import Path
from datetime import datetime

DATA_LAB = Path(r'C:\QuantLab\Data_Lab')
CATALYST_DB = DATA_LAB / 'catalyst_analysis_db'
WATCHLISTS = DATA_LAB / 'watchlists'
CONFIG = DATA_LAB / 'config'


def write_output(subdir: str, filename: str, data: dict, collector_name: str) -> Path:
    """Write collector output as JSON to catalyst_analysis_db/{subdir}/{filename}.

    Wraps the data in a standard envelope with timestamp and collector name.
    Returns the path to the written file.
    """
    envelope = {
        'updated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'collector': collector_name,
        'status': 'ok',
        'data': data,
    }
    out_dir = CATALYST_DB / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(json.dumps(envelope, indent=2, default=str), encoding='utf-8')
    return out_path


def read_output(subdir: str, filename: str = 'latest.json') -> dict:
    """Read a collector's JSON output. Returns empty dict if missing/corrupt."""
    path = CATALYST_DB / subdir / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def load_config(name: str) -> dict | list:
    """Load a config JSON file from the config/ directory."""
    path = CONFIG / f'{name}.json'
    return json.loads(path.read_text(encoding='utf-8'))


def load_watchlist(name: str):
    """Load a watchlist CSV as a pandas DataFrame. Adds .csv if needed."""
    import pandas as pd
    if not name.endswith('.csv'):
        name = f'{name}.csv'
    path = WATCHLISTS / name
    return pd.read_csv(path)


def safe_api_call(fn, *args, default=None, label='API call', **kwargs):
    """Call fn(*args, **kwargs) with try/except. Returns default on failure."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"  ⚠ {label} failed: {e}")
        return default


def parse_args(description: str) -> argparse.Namespace:
    """Standard argument parser with --dry-run flag.
    Also reconfigures stdout to UTF-8 so emoji print correctly on Windows.
    """
    # Windows terminal encoding fix — safe no-op on other platforms
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--dry-run', action='store_true',
                        help='Print what would be collected without writing')
    return parser.parse_args()


def fmt_pct(value, decimals=2) -> str:
    """Format a float as a percentage string like '+3.45%' or '-1.20%'."""
    if value is None:
        return '—'
    sign = '+' if value >= 0 else ''
    return f'{sign}{value:.{decimals}f}%'


def fmt_number(value, decimals=1, prefix='', suffix='') -> str:
    """Format a number with optional prefix/suffix. Returns '—' for None."""
    if value is None:
        return '—'
    if abs(value) >= 1_000_000_000_000:
        return f'{prefix}{value / 1_000_000_000_000:.{decimals}f}T{suffix}'
    if abs(value) >= 1_000_000_000:
        return f'{prefix}{value / 1_000_000_000:.{decimals}f}B{suffix}'
    if abs(value) >= 1_000_000:
        return f'{prefix}{value / 1_000_000:.{decimals}f}M{suffix}'
    return f'{prefix}{value:,.{decimals}f}{suffix}'


def color_class(value) -> str:
    """Return CSS class name for positive/negative/neutral values."""
    if value is None:
        return ''
    if value > 0:
        return 'positive'
    if value < 0:
        return 'negative'
    return ''

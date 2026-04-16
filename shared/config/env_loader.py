"""Environment key loader for local key files.

Loads keys from `shared/config/keys/{env}.env` into os.environ.
Also auto-loads the root .env on import for FRED, FMP, Tiingo, etc.

Usage:
  from shared.config.env_loader import load_keys
  load_keys('paper')   # or 'live'
"""
from pathlib import Path
import os
from typing import Dict


# ── Auto-load root .env on import (FRED, FMP, Tiingo, etc.) ──────────────────
def _load_root_env():
    try:
        from dotenv import load_dotenv
        root_env = Path(__file__).resolve().parents[2] / '.env'
        if root_env.exists():
            load_dotenv(root_env, override=False)
    except ImportError:
        pass

_load_root_env()


# ── Key file reader ───────────────────────────────────────────────────────────
def _read_env_file(path: Path) -> Dict[str, str]:
    result = {}
    if not path.exists():
        return result
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        result[k.strip()] = v.strip().strip('"\'')
    return result


# ── Primary loader ────────────────────────────────────────────────────────────
_ALPACA_KEYS = {
    'ALPACA_API_KEY', 'ALPACA_API_SECRET',
    'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY',
    'APCA_API_BASE_URL', 'ALPACA_API_BASE_URL',
}

_ALL_ALLOWED_KEYS = _ALPACA_KEYS | {
    'FRED_API_KEY',
    'FMP_API_KEY',
    'TIINGO_API_KEY',
    'ALPHA_VANTAGE_API_KEY',
    'USDA_API_KEY',
    'ANTHROPIC_API_KEY',
}


def load_keys(env_name: str, override: bool = False) -> Dict[str, str]:
    """Load all allowed keys from `shared/config/keys/{env_name}.env`.

    Injects them into os.environ. Returns dict of key names that were loaded.
    """
    repo_root = Path(__file__).resolve().parents[2]
    key_file = repo_root / 'shared' / 'config' / 'keys' / f"{env_name}.env"
    data = _read_env_file(key_file)
    loaded = {}
    for k, v in data.items():
        if k not in _ALL_ALLOWED_KEYS:
            continue
        if override or not os.getenv(k):
            os.environ[k] = v
            loaded[k] = '<loaded>'
        else:
            loaded[k] = '<present>'

    # Map ALPACA_* to APCA_* equivalents so both naming conventions work
    try:
        if os.getenv('ALPACA_API_KEY') and not os.getenv('APCA_API_KEY_ID'):
            os.environ['APCA_API_KEY_ID'] = os.environ['ALPACA_API_KEY']
            loaded.setdefault('APCA_API_KEY_ID', '<mapped>')
        if os.getenv('ALPACA_API_SECRET') and not os.getenv('APCA_API_SECRET_KEY'):
            os.environ['APCA_API_SECRET_KEY'] = os.environ['ALPACA_API_SECRET']
            loaded.setdefault('APCA_API_SECRET_KEY', '<mapped>')
        if os.getenv('ALPACA_API_BASE_URL') and not os.getenv('APCA_API_BASE_URL'):
            os.environ['APCA_API_BASE_URL'] = os.environ['ALPACA_API_BASE_URL']
            loaded.setdefault('APCA_API_BASE_URL', '<mapped>')
    except Exception:
        pass

    return loaded


def set_alpaca_env(env_name: str) -> Dict[str, str]:
    """Set ALPACA_ENV and load keys for that env."""
    os.environ['ALPACA_ENV'] = env_name
    return load_keys(env_name)


def ensure_env_loaded():
    """No-op — loading happens at module import time."""
    pass

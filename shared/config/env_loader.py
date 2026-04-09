"""Environment key loader for local key files.

This loader reads allowed key files from `shared/config/keys/{env}.env`
and loads them into `os.environ` for the current process only.

Usage:
  from shared.config.env_loader import load_keys
  load_keys('paper')

It intentionally avoids printing secret values.
"""
from pathlib import Path
import os
from typing import Dict


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


def load_keys(env_name: str, override: bool = False) -> Dict[str, str]:
    """Load allowed Alpaca key names from `shared/config/keys/{env_name}.env`.

    Keys are injected into `os.environ` only if they are not already set.
    Returns the dict of keys that were loaded (names without values masked).
    """
    repo_root = Path(__file__).resolve().parents[2]
    key_file = repo_root / 'shared' / 'config' / 'keys' / f"{env_name}.env"
    data = _read_env_file(key_file)
    allowed = {'ALPACA_API_KEY', 'ALPACA_API_SECRET', 'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'APCA_API_BASE_URL', 'ALPACA_API_BASE_URL'}
    loaded = {}
    for k, v in data.items():
        if k in allowed and (override or not os.getenv(k)):
            os.environ[k] = v
            loaded[k] = '<loaded>'
        elif k in allowed:
            loaded[k] = '<present>'
    # Map ALPACA_* names to APCA_* equivalents so code using either naming convention works
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
    """Helper to set `ALPACA_ENV` and load keys for that env.

    Returns loaded key names.
    """
    os.environ['ALPACA_ENV'] = env_name
    return load_keys(env_name)
"""
Environment Loader
------------------
Centralized .env loading for all API configurations.
Import this module first to ensure environment variables are loaded.
"""

from dotenv import load_dotenv, find_dotenv
import os

# Load .env file automatically on import
# override=False means existing environment variables take precedence
_env_file = find_dotenv()
if _env_file:
    load_dotenv(_env_file, override=False)
else:
    # Try to find .env in project root
    import sys
    from pathlib import Path
    
    # Get project root (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / '.env'
    
    if env_path.exists():
        load_dotenv(env_path, override=False)


def ensure_env_loaded():
    """
    Explicitly ensure environment is loaded.
    This is called automatically on module import, but can be called manually if needed.
    """
    pass  # Loading happens at module import time

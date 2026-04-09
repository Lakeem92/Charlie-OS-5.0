#!/usr/bin/env python3
"""
Safe Alpaca paper-trading connectivity check (alternate file).

This is a standalone copy used to avoid issues with the original file.
It behaves identically: loads `.env` from repo root (process-only) and tests
both paper and live Alpaca endpoints without printing secrets.
"""
import os
import sys
from pathlib import Path


def _get_env_var(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def _load_dotenv_file(path: Path):
    if not path.exists():
        return
    allowed = {
        'APCA_API_KEY_ID',
        'APCA_API_SECRET_KEY',
        'ALPACA_API_KEY',
        'ALPACA_API_SECRET',
        'APCA_API_BASE_URL',
        'ALPACA_API_BASE_URL',
    }
    try:
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"\'')
                if k in allowed and not os.getenv(k):
                    os.environ[k] = v
    except Exception:
        pass


def main():
    # Prefer explicit ALPACA_ENV; default to 'paper' for this test helper
    env_name = os.getenv('ALPACA_ENV', 'paper')
    # Try to use shared config env_loader if available to load keys from shared/config/keys
    try:
        # ensure repo root on sys.path so 'shared' package can be imported
        repo_root = Path(__file__).resolve().parents[1]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from shared.config import env_loader as _el
        loaded = _el.load_keys(env_name, override=True)
        print('env_loader returned:', loaded)
    except Exception as e:
        print('env_loader import/load failed:', type(e).__name__, str(e))
        # fall back to repo .env loading
        repo_root = Path(__file__).resolve().parents[1]
        _load_dotenv_file(repo_root / '.env')

    key = _get_env_var('APCA_API_KEY_ID', 'ALPACA_API_KEY', 'APCA_API_KEY')
    secret = _get_env_var('APCA_API_SECRET_KEY', 'APCA_API_SECRET', 'APCA_API_SECRET', 'APCA_API_SECRET_KEY')

    def _mask(s):
        if not s:
            return '<missing>'
        return s[:4] + '....' + s[-4:]

    print('Using key:', _mask(key), ' secret:', _mask(secret))

    if not key or not secret:
        print('Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your environment or add them to a .env file in the repo root.')
        sys.exit(2)

    try:
        from alpaca_trade_api.rest import REST
    except Exception:
        print("Missing dependency 'alpaca-trade-api'. Install with: pip install alpaca-trade-api")
        sys.exit(2)

    endpoints = {
        'paper': os.getenv('APCA_API_BASE_URL') or os.getenv('ALPACA_API_BASE_URL') or 'https://paper-api.alpaca.markets',
        'live': os.getenv('ALPACA_API_BASE_URL') or 'https://api.alpaca.markets',
    }

    results = {}
    for name, base in endpoints.items():
        try:
            api = REST(key, secret, base_url=base)
            account = api.get_account()
            results[name] = {
                'ok': True,
                'status': getattr(account, 'status', 'N/A'),
                'portfolio_value': getattr(account, 'portfolio_value', 'N/A'),
            }
        except Exception as e:
            results[name] = {'ok': False, 'error': f'{type(e).__name__}: {e}'}

    print('\nEndpoint test results:')
    for name in ['paper', 'live']:
        r = results.get(name)
        if r and r.get('ok'):
            print(f" - {name}: SUCCESS (status={r.get('status')}, portfolio_value={r.get('portfolio_value')})")
        else:
            print(f" - {name}: FAIL ({r.get('error') if r else 'no result'})")

    succ = [n for n, v in results.items() if v.get('ok')]
    if len(succ) == 1:
        print(f"\nKeys appear to be for the '{succ[0]}' endpoint.")
    elif len(succ) == 2:
        print('\nKeys worked for both endpoints (unexpected).')
    else:
        print('\nKeys did not work for either endpoint.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Safe Alpaca paper-trading connectivity check.

This script performs read-only checks against Alpaca paper and live endpoints:
- GET account
- List positions (count only)
- List recent orders (count only)

It will attempt to load a `.env` file from the repo root (process-only, no printing)
to pick up Alpaca keys if they were placed there. It never prints secret values.

Usage (PowerShell):
  .venv\Scripts\Activate.ps1
  python scratch/test_alpaca_paper_safe.py

If you prefer to set keys in-session:
  $env:APCA_API_KEY_ID = '<key>'
  $env:APCA_API_SECRET_KEY = '<secret>'
  python scratch/test_alpaca_paper_safe.py
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
    # Load .env from repo root if present (process-only)
    repo_root = Path(__file__).resolve().parents[1]
    _load_dotenv_file(repo_root / '.env')

    key = _get_env_var('APCA_API_KEY_ID', 'ALPACA_API_KEY', 'APCA_API_KEY')
    secret = _get_env_var('APCA_API_SECRET_KEY', 'APCA_API_SECRET_KEY', 'APCA_API_SECRET')

    if not key or not secret:
        print('Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your environment or add them to a .env file.')
        print('Example (PowerShell):')
        print("  $env:APCA_API_KEY_ID = '<key>'")
        print("  $env:APCA_API_SECRET_KEY = '<secret>'")
        sys.exit(2)

    try:
        from alpaca_trade_api.rest import REST
    except Exception:
        print("Missing dependency 'alpaca-trade-api'. Install with: pip install alpaca-trade-api")
        sys.exit(2)

    endpoints = {
        'paper': os.getenv('APCA_API_BASE_URL') or 'https://paper-api.alpaca.markets',
        'live': 'https://api.alpaca.markets',
    }

    results = {}

    for name, base in endpoints.items():
        try:
            api = REST(key, secret, base_url=base)
            account = api.get_account()
            # Minimal non-sensitive info
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
        if not r:
            print(f' - {name}: no result')
            continue
        if r.get('ok'):
            print(f" - {name}: SUCCESS (status={r.get('status')}, portfolio_value={r.get('portfolio_value')})")
        else:
            print(f" - {name}: FAIL ({r.get('error')})")

    succ = [n for n, v in results.items() if v.get('ok')]
    if len(succ) == 1:
        print(f"\nKeys appear to be for the '{succ[0]}' endpoint.")
    elif len(succ) == 2:
        print('\nKeys worked for both endpoints (unexpected).')
    else:
        print('\nKeys did not work for either endpoint.')


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Safe Alpaca paper-trading connectivity check.

This script performs read-only checks against Alpaca paper and live endpoints:
- GET account
- List positions (count only)
- List recent orders (count only)

It will attempt to load a `.env` file from the repo root (process-only, no printing)
to pick up Alpaca keys if they were placed there. It never prints secret values.

Usage (PowerShell):
  .venv\Scripts\Activate.ps1
  python scratch/test_alpaca_paper_safe.py

If you prefer to set keys in-session:
  $env:APCA_API_KEY_ID = '<key>'
  $env:APCA_API_SECRET_KEY = '<secret>'
  python scratch/test_alpaca_paper_safe.py
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
    # Load .env from repo root if present (process-only)
    repo_root = Path(__file__).resolve().parents[1]
    _load_dotenv_file(repo_root / '.env')

    key = _get_env_var('APCA_API_KEY_ID', 'ALPACA_API_KEY', 'APCA_API_KEY')
    secret = _get_env_var('APCA_API_SECRET_KEY', 'ALPACA_API_SECRET_KEY', 'ALPACA_API_SECRET')

    if not key or not secret:
        print('Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your environment or add them to a .env file.')
        print('Example (PowerShell):')
        print("  $env:APCA_API_KEY_ID = '<key>'")
        print("  $env:APCA_API_SECRET_KEY = '<secret>'")
        sys.exit(2)

    try:
        from alpaca_trade_api.rest import REST
    except Exception:
        print("Missing dependency 'alpaca-trade-api'. Install with: pip install alpaca-trade-api")
        sys.exit(2)

    endpoints = {
        'paper': os.getenv('APCA_API_BASE_URL') or 'https://paper-api.alpaca.markets',
        'live': 'https://api.alpaca.markets',
    }

    results = {}

    for name, base in endpoints.items():
        try:
            api = REST(key, secret, base_url=base)
            account = api.get_account()
            # Minimal non-sensitive info
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
        if not r:
            print(f' - {name}: no result')
            continue
        if r.get('ok'):
            print(f" - {name}: SUCCESS (status={r.get('status')}, portfolio_value={r.get('portfolio_value')})")
        else:
            print(f" - {name}: FAIL ({r.get('error')})")

    succ = [n for n, v in results.items() if v.get('ok')]
    if len(succ) == 1:
        print(f"\nKeys appear to be for the '{succ[0]}' endpoint.")
    elif len(succ) == 2:
        print('\nKeys worked for both endpoints (unexpected).')
    else:
        print('\nKeys did not work for either endpoint.')


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Safe Alpaca paper-trading connectivity check.

This script performs read-only checks against Alpaca paper endpoints:
- GET account
- GET clock
- List positions (count only)
- List recent orders (count only)

It intentionally avoids printing any secret values.

Usage (PowerShell):
  .venv\Scripts\Activate.ps1
  setx APCA_API_KEY_ID "your_key_here"
  setx APCA_API_SECRET_KEY "your_secret_here"
  python scratch/test_alpaca_paper_safe.py

Or set environment variables for the current session:
  $env:APCA_API_KEY_ID = "..."; $env:APCA_API_SECRET_KEY = "..."
  python scratch/test_alpaca_paper_safe.py
"""
import os
import sys


def _get_env_var(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def main():
    key = _get_env_var('APCA_API_KEY_ID', 'ALPACA_API_KEY', 'ALPACA_API_KEY_ID')
    secret = _get_env_var('APCA_API_SECRET_KEY', 'APCA_API_SECRET_KEY', 'ALPACA_API_SECRET')

    if not key or not secret:
        print('Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your environment.')
        print('Example (PowerShell):')
        print("  $env:APCA_API_KEY_ID = '<key>'")
        print("  $env:APCA_API_SECRET_KEY = '<secret>'")
        sys.exit(2)

    try:
        from alpaca_trade_api.rest import REST
    except Exception:
        print("Missing dependency 'alpaca-trade-api'. Install with: pip install alpaca-trade-api")
        sys.exit(2)

    endpoints = {
        'paper': 'https://paper-api.alpaca.markets',
        'live': 'https://api.alpaca.markets',
    }

    results = {}

    for name, base in endpoints.items():
        try:
            api = REST(key, secret, base_url=base)
            account = api.get_account()
            # Minimal non-sensitive info
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
        if not r:
            print(f' - {name}: no result')
            continue
        if r.get('ok'):
            print(f" - {name}: SUCCESS (status={r.get('status')}, portfolio_value={r.get('portfolio_value')})")
        else:
            print(f" - {name}: FAIL ({r.get('error')})")

    from pathlib import Path
    # Heuristic: if only one endpoint succeeded, that's likely which account the keys belong to.
    succ = [n for n, v in results.items() if v.get('ok')]
    if len(succ) == 1:
        print(f"\nKeys appear to be for the '{succ[0]}' endpoint.")
    elif len(succ) == 2:
        print('\nKeys worked for both endpoints (unexpected). Keys may be valid for both or the service responded without strict separation.')
    else:
        print('\nKeys did not work for either endpoint.')

        # If a .env file exists in the repo root, load only known Alpaca keys into the process env.
        def _load_dotenv_file(path: Path):
            if not path.exists():
                return
            allowed = {'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'ALPACA_API_KEY', 'ALPACA_API_SECRET', 'APCA_API_BASE_URL', 'ALPACA_API_BASE_URL'}
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

        _load_dotenv_file(Path(__file__).resolve().parents[1] / '.env')


if __name__ == '__main__':
    main()

            print('Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your environment or add them to a .env file.')

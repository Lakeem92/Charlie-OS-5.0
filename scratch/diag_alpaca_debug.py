#!/usr/bin/env python3
"""Diagnostic: load keys, show masked env state, and GET account endpoint with requests."""
import os
import sys
from pathlib import Path
# Ensure repo root is on sys.path so `shared.config` imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
from shared.config import env_loader
import requests


def mask(v: str) -> str:
    if not v:
        return '<missing>'
    if len(v) <= 8:
        return v[:2] + '....' + v[-2:]
    return v[:4] + '....' + v[-4:]


def main():
    env = 'paper'
    print('Loading keys for:', env)
    loaded = env_loader.load_keys(env, override=True)
    print('loaded keys:', loaded)

    # Show which env names are present (masked)
    names = ['ALPACA_API_KEY', 'ALPACA_API_SECRET', 'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'ALPACA_API_BASE_URL', 'APCA_API_BASE_URL']
    for n in names:
        print(f'{n}:', mask(os.getenv(n)))

    # Build header set prioritized
    key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
    secret = os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_API_SECRET')
    base = os.getenv('APCA_API_BASE_URL') or os.getenv('ALPACA_API_BASE_URL') or 'https://paper-api.alpaca.markets'

    print('\nUsing base URL:', base)
    headers = {'APCA-API-KEY-ID': key or '', 'APCA-API-SECRET-KEY': secret or ''}

    print('Making direct HTTP GET to account endpoint (no SDK)')
    try:
        resp = requests.get(f"{base}/v2/account", headers=headers, timeout=10)
        print('HTTP', resp.status_code)
        txt = resp.text
        if resp.status_code != 200:
            print('Response text (truncated):', txt[:400].replace('\n',' '))
        else:
            # show minimal non-sensitive account fields
            j = resp.json()
            print('account_status:', j.get('status'))
            print('portfolio_value:', j.get('portfolio_value'))
    except Exception as e:
        print('Request error:', type(e).__name__, str(e))

    # Now try via SDK to reproduce test script behavior
    print('\nAttempting SDK call via alpaca_trade_api.REST')
    try:
        from alpaca_trade_api.rest import REST
        sdk = REST(key, secret, base_url=base)
        acc = sdk.get_account()
        print('SDK account_status:', getattr(acc, 'status', None))
        print('SDK portfolio_value:', getattr(acc, 'portfolio_value', None))
    except Exception as e:
        print('SDK error:', type(e).__name__, str(e))


if __name__ == '__main__':
    main()

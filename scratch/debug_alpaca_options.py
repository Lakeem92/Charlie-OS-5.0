"""Quick debug script to inspect Alpaca options endpoints."""
import requests, os, json
from dotenv import load_dotenv

load_dotenv("shared/config/keys/paper.env", override=True)
key = os.environ.get("ALPACA_API_KEY", "")
sec = os.environ.get("ALPACA_API_SECRET", "")
headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}

# 1) Try contracts endpoint
print("=== CONTRACTS ENDPOINT ===")
url = "https://data.alpaca.markets/v1beta1/options/contracts"
params = {"underlying_symbols": "SPY", "status": "active", "limit": 2}
r = requests.get(url, headers=headers, params=params)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    for c in data.get("option_contracts", [])[:2]:
        print(json.dumps(c, indent=2, default=str))
    print(f"next_page_token present: {bool(data.get('next_page_token'))}")
else:
    print(r.text[:500])

print()

# 2) Try snapshots with opra feed
print("=== SNAPSHOTS WITH OPRA FEED ===")
url2 = "https://data.alpaca.markets/v1beta1/options/snapshots/SPY"
params2 = {"feed": "opra", "limit": 2}
r2 = requests.get(url2, headers=headers, params=params2)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    data2 = r2.json()
    for sym, snap in list(data2.get("snapshots", {}).items())[:2]:
        print(f"--- {sym} ---")
        print(json.dumps(snap, indent=2, default=str))
else:
    print(r2.text[:500])

print()

# 3) Try snapshots with indicative + look for all keys
print("=== SNAPSHOT KEY INSPECTION (indicative) ===")
url3 = "https://data.alpaca.markets/v1beta1/options/snapshots/SPY"
params3 = {"feed": "indicative", "limit": 5}
r3 = requests.get(url3, headers=headers, params=params3)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    data3 = r3.json()
    for sym, snap in list(data3.get("snapshots", {}).items())[:5]:
        keys = sorted(snap.keys())
        print(f"{sym}: keys={keys}")

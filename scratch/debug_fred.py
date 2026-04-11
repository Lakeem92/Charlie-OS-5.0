import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

print("=" * 60)
print("FRED API FULL DIAGNOSTIC")
print("=" * 60)

# ── STEP 1: Find every .env file that exists ─────────────────
from pathlib import Path
root = Path(r'C:\QuantLab\Data_Lab')

print("\n[1/5] SCANNING FOR .ENV FILES...")
env_locations = [
    root / '.env',
    root / 'shared' / 'config' / 'keys' / 'paper.env',
    root / 'shared' / 'config' / 'keys' / 'live.env',
    root / 'tools' / 'levels_engine' / '.env',
]
for p in env_locations:
    exists = p.exists()
    print(f"  {'OK' if exists else 'MISSING'} {p}")
    if exists:
        content = p.read_text(encoding='utf-8')
        has_fred = 'FRED_API_KEY' in content
        print(f"      Contains FRED_API_KEY: {'YES' if has_fred else 'NO'}")

# ── STEP 2: Check os.environ right now ──────────────────────
print("\n[2/5] CHECKING os.environ FOR FRED KEY...")
fred_key = os.environ.get('FRED_API_KEY')
if fred_key:
    print(f"  FOUND in environment: {fred_key[:6]}...{fred_key[-4:]}")
else:
    print("  NOT in os.environ yet")

# ── STEP 3: Try loading via dotenv directly ──────────────────
print("\n[3/5] TRYING python-dotenv LOAD FROM ROOT .env...")
try:
    from dotenv import load_dotenv
    root_env = root / '.env'
    if root_env.exists():
        load_dotenv(root_env, override=True)
        fred_key = os.environ.get('FRED_API_KEY')
        if fred_key:
            print(f"  Loaded! FRED_API_KEY: {fred_key[:6]}...{fred_key[-4:]}")
        else:
            print("  Loaded .env but FRED_API_KEY still missing -- add it to root .env")
    else:
        print("  Root .env does not exist -- need to create it")
except ImportError:
    print("  python-dotenv not installed")

# ── STEP 4: Test FREDClient wrapper ─────────────────────────
print("\n[4/5] TESTING FREDClient WRAPPER...")
try:
    from shared.config.api_clients import FREDClient
    fred_client = FREDClient()
    result = fred_client.get_series('VIXCLS')
    print(f"  FREDClient result type: {type(result)}")
    print(f"  FREDClient result preview: {str(result)[:200]}")
except Exception as e:
    print(f"  FREDClient failed: {e}")

# ── STEP 5: Test fredapi direct ──────────────────────────────
print("\n[5/5] TESTING fredapi DIRECT...")
try:
    import fredapi
    key = os.environ.get('FRED_API_KEY')
    if not key:
        print("  Still no FRED_API_KEY -- cannot test fredapi")
    else:
        fred = fredapi.Fred(api_key=key)
        vix = fred.get_series('VIXCLS', observation_start='2025-01-01')
        hy = fred.get_series('BAMLH0A0HYM2', observation_start='2025-01-01')
        yc = fred.get_series('T10Y2Y', observation_start='2025-01-01')
        print(f"  VIX (VIXCLS): {len(vix)} rows, latest = {vix.iloc[-1]:.2f}")
        print(f"  HY Spread (BAMLH0A0HYM2): {len(hy)} rows, latest = {hy.iloc[-1]:.2f}")
        print(f"  Yield Curve (T10Y2Y): {len(yc)} rows, latest = {yc.iloc[-1]:.2f}")
        print("\n  fredapi works -- dashboard can use this directly")
except ImportError:
    print("  fredapi not installed -- run: pip install fredapi")
except Exception as e:
    print(f"  fredapi error: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

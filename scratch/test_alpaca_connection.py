"""
Quick Alpaca API Connection Test
Tests historical data retrieval with proper time ranges for Basic plan
"""

from alpaca_trade_api import REST
from datetime import datetime, timedelta
import pytz
import os

# Initialize client using environment variables
try:
    # Try environment variables first
    api_key = os.getenv('ALPACA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY') or os.getenv('ALPACA_API_SECRET')
    
    if not api_key or not api_secret:
        print("⚠️ Environment variables not found, trying .env file...")
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('ALPACA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY') or os.getenv('ALPACA_API_SECRET')
    
    api = REST(
        key_id=api_key,
        secret_key=api_secret,
        base_url='https://paper-api.alpaca.markets'
    )
    print("✅ Alpaca API Client Initialized Successfully!")
    print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
except Exception as e:
    print(f"❌ Failed to initialize Alpaca Client. Error: {e}")
    exit()

# Set time range: 30 minutes in the past to respect the Basic plan limit
utc_now = datetime.now(pytz.utc)
end_time_utc = utc_now - timedelta(minutes=30)
start_time_utc = end_time_utc - timedelta(days=1)

print(f"\n📊 Fetching AAPL data:")
print(f"   Start: {start_time_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"   End:   {end_time_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Pull 1-minute historical bars for AAPL
try:
    bars = api.get_bars(
        'AAPL',
        timeframe='1Min',
        start=start_time_utc.isoformat(),
        end=end_time_utc.isoformat(),
        limit=10 
    ).df
    
    if not bars.empty:
        print(f"\n✅ SUCCESS! Fetched {len(bars)} historical bars for AAPL.")
        print("\n--- Sample Data Head ---")
        print(bars.head())
        print(f"\n📈 Latest bar:")
        print(f"   Time: {bars.index[-1]}")
        print(f"   Open: ${bars.iloc[-1]['open']:.2f}")
        print(f"   High: ${bars.iloc[-1]['high']:.2f}")
        print(f"   Low: ${bars.iloc[-1]['low']:.2f}")
        print(f"   Close: ${bars.iloc[-1]['close']:.2f}")
        print(f"   Volume: {bars.iloc[-1]['volume']:,.0f}")
    else:
        print(f"\n⚠️ WARNING: Fetched 0 bars. Time range may be too recent or symbol unavailable.")

except Exception as e:
    print(f"\n❌ FAILED to fetch data. Error: {e}")
    print("\nTrying alternative method with daily bars...")
    
    # Fallback: Try daily bars which have no delay
    try:
        bars = api.get_bars(
            'AAPL',
            timeframe='1Day',
            start=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d'),
            limit=5
        ).df
        
        if not bars.empty:
            print(f"✅ Fetched {len(bars)} daily bars for AAPL (last 5 days)")
            print(bars)
        else:
            print("⚠️ No daily data available")
    except Exception as e2:
        print(f"❌ Daily bars also failed: {e2}")

print("\n" + "="*60)
print("✓ Test Complete")
print("="*60)

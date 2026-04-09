"""
Alpaca API Test - Daily Bars and Account Info
Testing with daily data which has no delay restrictions
"""

from alpaca_trade_api import REST
from datetime import datetime, timedelta
import os

# Initialize client
try:
    api_key = os.getenv('ALPACA_API_KEY_ID') or 'AKVHW7MJIBMFAMWQ7E52J32C74'
    api_secret = os.getenv('ALPACA_SECRET_KEY') or '27ESXP19ABA1FSaN5gcTtHAWUBWroeULTPX376vp3CBk'
    
    api = REST(
        key_id=api_key,
        secret_key=api_secret,
        base_url='https://paper-api.alpaca.markets'
    )
    print("✅ Alpaca API Client Initialized Successfully!\n")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    exit()

# Test 1: Account Info
print("="*70)
print("TEST 1: ACCOUNT INFORMATION")
print("="*70)
try:
    account = api.get_account()
    print(f"Account ID: {account.id}")
    print(f"Status: {account.status}")
    print(f"Currency: {account.currency}")
    print(f"Buying Power: ${float(account.buying_power):,.2f}")
    print(f"Cash: ${float(account.cash):,.2f}")
    print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"Pattern Day Trader: {account.pattern_day_trader}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Market Clock
print("\n" + "="*70)
print("TEST 2: MARKET CLOCK")
print("="*70)
try:
    clock = api.get_clock()
    print(f"Market is: {'🟢 OPEN' if clock.is_open else '🔴 CLOSED'}")
    print(f"Current time: {clock.timestamp}")
    print(f"Next open: {clock.next_open}")
    print(f"Next close: {clock.next_close}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Daily Bars for BABA (last 10 trading days)
print("\n" + "="*70)
print("TEST 3: HISTORICAL DAILY BARS - BABA")
print("="*70)
try:
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
    
    print(f"Fetching data from {start_date} to {end_date}...")
    
    bars = api.get_bars(
        'BABA',
        timeframe='1Day',
        start=start_date,
        end=end_date,
        limit=10
    ).df
    
    if not bars.empty:
        print(f"\n✅ SUCCESS! Fetched {len(bars)} daily bars for BABA\n")
        print(f"{'Date':<12} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>12}")
        print("-" * 70)
        
        for idx, row in bars.iterrows():
            date_str = idx.strftime('%Y-%m-%d')
            print(f"{date_str:<12} ${row['open']:>7.2f} ${row['high']:>7.2f} ${row['low']:>7.2f} ${row['close']:>7.2f} {row['volume']:>12,.0f}")
        
        # Calculate some metrics
        latest_close = bars.iloc[-1]['close']
        prev_close = bars.iloc[-2]['close'] if len(bars) > 1 else latest_close
        change = ((latest_close - prev_close) / prev_close) * 100
        
        print(f"\n📊 Latest: ${latest_close:.2f} ({change:+.2f}%)")
    else:
        print("⚠️ No data returned")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Multiple symbols snapshot
print("\n" + "="*70)
print("TEST 4: MULTI-SYMBOL SNAPSHOT")
print("="*70)
try:
    symbols = ['BABA', 'AAPL', 'TSLA']
    print(f"Fetching latest data for: {', '.join(symbols)}\n")
    
    for symbol in symbols:
        try:
            # Get latest trade
            trade = api.get_latest_trade(symbol)
            quote = api.get_latest_quote(symbol)
            
            print(f"{symbol}:")
            print(f"  Last Trade: ${trade.price:.2f} @ {trade.timestamp}")
            print(f"  Bid: ${quote.bidprice:.2f} x {quote.bidsize}")
            print(f"  Ask: ${quote.askprice:.2f} x {quote.asksize}")
            print()
        except Exception as e:
            print(f"  ⚠️ Error for {symbol}: {e}\n")
            
except Exception as e:
    print(f"❌ Error: {e}")

print("="*70)
print("✓ ALL TESTS COMPLETE")
print("="*70)

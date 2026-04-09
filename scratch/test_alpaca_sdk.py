"""
Alpaca API Test - Using alpaca-py SDK
Tests with proper subscription tier handling
"""

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from datetime import datetime, timedelta
import os

# Setup credentials
API_KEY = os.getenv('ALPACA_API_KEY_ID') or 'AKVHW7MJIBMFAMWQ7E52J32C74'
API_SECRET = os.getenv('ALPACA_SECRET_KEY') or '27ESXP19ABA1FSaN5gcTtHAWUBWroeULTPX376vp3CBk'

print("="*70)
print("ALPACA API TEST - Using alpaca-py SDK")
print("="*70 + "\n")

# Test 1: Historical Data Client
print("TEST 1: HISTORICAL STOCK DATA")
print("-"*70)
try:
    data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
    print("✅ Data client initialized")
    
    # Request historical bars for BABA (last 5 days)
    request_params = StockBarsRequest(
        symbol_or_symbols=["BABA"],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=10),
        end=datetime.now()
    )
    
    bars = data_client.get_stock_bars(request_params)
    baba_bars = bars.df
    
    if not baba_bars.empty:
        print(f"✅ Fetched {len(baba_bars)} bars for BABA\n")
        
        # Reset index to show dates
        baba_bars = baba_bars.reset_index()
        
        print(f"{'Date':<20} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>12}")
        print("-"*70)
        
        for _, row in baba_bars.iterrows():
            date_str = row['timestamp'].strftime('%Y-%m-%d %H:%M')
            print(f"{date_str:<20} ${row['open']:>7.2f} ${row['high']:>7.2f} ${row['low']:>7.2f} ${row['close']:>7.2f} {row['volume']:>12,.0f}")
        
        # Latest price
        latest = baba_bars.iloc[-1]
        prev = baba_bars.iloc[-2] if len(baba_bars) > 1 else latest
        change = ((latest['close'] - prev['close']) / prev['close']) * 100
        
        print(f"\n📊 BABA Latest: ${latest['close']:.2f} ({change:+.2f}%)")
    else:
        print("⚠️ No data returned")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Latest Trades
print("\n" + "="*70)
print("TEST 2: LATEST TRADES")
print("-"*70)
try:
    symbols = ['BABA', 'AAPL', 'TSLA']
    
    for symbol in symbols:
        try:
            request_params = StockLatestTradeRequest(symbol_or_symbols=symbol)
            latest_trade = data_client.get_stock_latest_trade(request_params)
            
            trade = latest_trade[symbol]
            print(f"{symbol:6} Last: ${trade.price:>7.2f} | Size: {trade.size:>6} | Time: {trade.timestamp}")
        except Exception as e:
            print(f"{symbol:6} ⚠️ {e}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Multi-symbol bars
print("\n" + "="*70)
print("TEST 3: MULTI-SYMBOL COMPARISON")
print("-"*70)
try:
    # Get last 2 days for multiple symbols
    request_params = StockBarsRequest(
        symbol_or_symbols=["BABA", "AAPL", "JD", "BIDU"],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=5),
        end=datetime.now()
    )
    
    multi_bars = data_client.get_stock_bars(request_params)
    
    print(f"\n{'Symbol':<8} {'Latest Close':>12} {'Prev Close':>12} {'Change %':>10}")
    print("-"*70)
    
    for symbol in ["BABA", "AAPL", "JD", "BIDU"]:
        try:
            symbol_data = multi_bars.df[multi_bars.df.index.get_level_values('symbol') == symbol]
            
            if len(symbol_data) >= 2:
                latest = symbol_data.iloc[-1]['close']
                prev = symbol_data.iloc[-2]['close']
                change = ((latest - prev) / prev) * 100
                
                print(f"{symbol:<8} ${latest:>11.2f} ${prev:>11.2f} {change:>9.2f}%")
            else:
                print(f"{symbol:<8} ⚠️ Insufficient data")
        except Exception as e:
            print(f"{symbol:<8} ⚠️ {e}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Trading Client (Account info)
print("\n" + "="*70)
print("TEST 4: TRADING ACCOUNT")
print("-"*70)
try:
    trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
    print("✅ Trading client initialized (Paper Trading)")
    
    try:
        account = trading_client.get_account()
        print(f"\nAccount Number: {account.account_number}")
        print(f"Status: {account.status}")
        print(f"Buying Power: ${float(account.buying_power):,.2f}")
        print(f"Cash: ${float(account.cash):,.2f}")
        print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"Equity: ${float(account.equity):,.2f}")
    except Exception as e:
        print(f"⚠️ Account info not available: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ ALL TESTS COMPLETE")
print("="*70)
print("\n💡 Note: Some features may be limited by your Alpaca subscription tier.")
print("   Historical data and account features work best with funded accounts.")

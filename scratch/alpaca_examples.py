"""
Alpaca API Examples - Trading & Market Data
Quick reference for using the Alpaca client
"""

from config.api_clients import AlpacaClient
from datetime import datetime, timedelta


def example_account_info():
    """Get account information"""
    print("\n" + "="*70)
    print("ALPACA ACCOUNT INFORMATION")
    print("="*70 + "\n")
    
    client = AlpacaClient(paper_trading=True)
    
    try:
        account = client.get_account()
        print(f"Account Status: {account.get('status')}")
        print(f"Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
        print(f"Cash: ${float(account.get('cash', 0)):,.2f}")
        print(f"Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
        print(f"Day Trading Buying Power: ${float(account.get('daytrading_buying_power', 0)):,.2f}")
        print(f"Pattern Day Trader: {account.get('pattern_day_trader')}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_market_data():
    """Get market data for stocks"""
    print("\n" + "="*70)
    print("MARKET DATA - SNAPSHOT")
    print("="*70 + "\n")
    
    client = AlpacaClient()
    symbols = ['BABA', 'AAPL', 'TSLA']
    
    try:
        snapshots = client.get_snapshots(symbols)
        
        for symbol, data in snapshots.items():
            latest_trade = data.get('latestTrade', {})
            latest_quote = data.get('latestQuote', {})
            prev_close = data.get('prevDailyBar', {}).get('c', 0)
            
            price = latest_trade.get('p', 0)
            change = ((price - prev_close) / prev_close * 100) if prev_close else 0
            
            print(f"{symbol}:")
            print(f"  Last Price: ${price:.2f}")
            print(f"  Change: {change:+.2f}%")
            print(f"  Bid: ${latest_quote.get('bp', 0):.2f} x {latest_quote.get('bs', 0)}")
            print(f"  Ask: ${latest_quote.get('ap', 0):.2f} x {latest_quote.get('as', 0)}")
            print()
    except Exception as e:
        print(f"❌ Error: {e}")


def example_historical_bars():
    """Get historical price data"""
    print("\n" + "="*70)
    print("HISTORICAL BARS - BABA (Last 5 Days)")
    print("="*70 + "\n")
    
    client = AlpacaClient()
    
    try:
        # Get last 5 days of daily data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        
        bars = client.get_bars(
            symbol='BABA',
            timeframe='1Day',
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            limit=5
        )
        
        if 'bars' in bars:
            print(f"{'Date':<12} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>12}")
            print("-" * 70)
            
            for bar in bars['bars']:
                date = bar['t'][:10]  # Extract date from timestamp
                print(f"{date:<12} ${bar['o']:>7.2f} ${bar['h']:>7.2f} ${bar['l']:>7.2f} ${bar['c']:>7.2f} {bar['v']:>12,}")
        else:
            print("No data returned")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_market_clock():
    """Check if market is open"""
    print("\n" + "="*70)
    print("MARKET CLOCK")
    print("="*70 + "\n")
    
    client = AlpacaClient()
    
    try:
        clock = client.get_clock()
        is_open = clock.get('is_open')
        next_open = clock.get('next_open')
        next_close = clock.get('next_close')
        
        print(f"Market is currently: {'🟢 OPEN' if is_open else '🔴 CLOSED'}")
        print(f"Next Open: {next_open}")
        print(f"Next Close: {next_close}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_positions():
    """Get current positions"""
    print("\n" + "="*70)
    print("CURRENT POSITIONS")
    print("="*70 + "\n")
    
    client = AlpacaClient(paper_trading=True)
    
    try:
        positions = client.get_positions()
        
        if not positions:
            print("No open positions")
        else:
            print(f"{'Symbol':<8} {'Qty':>8} {'Entry':>10} {'Current':>10} {'P&L':>10} {'P&L %':>8}")
            print("-" * 70)
            
            for pos in positions:
                symbol = pos['symbol']
                qty = float(pos['qty'])
                avg_entry = float(pos['avg_entry_price'])
                current = float(pos['current_price'])
                pnl = float(pos['unrealized_pl'])
                pnl_pct = float(pos['unrealized_plpc']) * 100
                
                print(f"{symbol:<8} {qty:>8.0f} ${avg_entry:>9.2f} ${current:>9.2f} ${pnl:>9.2f} {pnl_pct:>7.2f}%")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_place_order():
    """Example of placing an order (commented out for safety)"""
    print("\n" + "="*70)
    print("PLACING ORDERS (Example - Not Executed)")
    print("="*70 + "\n")
    
    print("Example code to place orders:\n")
    print("# Market order")
    print("order = client.place_order(")
    print("    symbol='BABA',")
    print("    qty=10,")
    print("    side='buy',")
    print("    order_type='market',")
    print("    time_in_force='day'")
    print(")\n")
    
    print("# Limit order")
    print("order = client.place_order(")
    print("    symbol='BABA',")
    print("    qty=10,")
    print("    side='buy',")
    print("    order_type='limit',")
    print("    time_in_force='day',")
    print("    limit_price=85.50")
    print(")\n")
    
    print("# Stop loss order")
    print("order = client.place_order(")
    print("    symbol='BABA',")
    print("    qty=10,")
    print("    side='sell',")
    print("    order_type='stop',")
    print("    time_in_force='gtc',")
    print("    stop_price=80.00")
    print(")\n")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("ALPACA API EXAMPLES")
    print("="*70)
    
    # Uncomment the examples you want to run:
    
    example_account_info()
    example_market_clock()
    example_market_data()
    example_historical_bars()
    example_positions()
    example_place_order()
    
    print("\n" + "="*70)
    print("✓ Examples Complete")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

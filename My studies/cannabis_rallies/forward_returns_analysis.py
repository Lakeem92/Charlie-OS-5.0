"""
Forward Returns Analysis - Cannabis Rally Endpoints
Calculates 1-day, 3-day, and 5-day forward returns from pivot dates.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_forward_returns(ticker, pivot_date, window_days=20):
    """
    Calculate forward returns from a pivot date.
    
    Args:
        ticker: Stock ticker symbol
        pivot_date: Date to calculate returns from (T)
        window_days: Days to fetch after pivot (buffer for weekends/holidays)
    
    Returns:
        Dict with 1-day, 3-day, and 5-day forward returns
    """
    # Convert to datetime
    pivot = pd.to_datetime(pivot_date)
    
    # Fetch data from pivot date forward
    start = pivot
    end = pivot + timedelta(days=window_days)
    
    print(f"\nFetching {ticker} data from {start.date()} to {end.date()}...")
    
    # Download data (auto_adjust=True by default now, Close is adjusted)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    
    if df.empty:
        print(f"  ⚠️ No data retrieved for {ticker}")
        return {
            '1_day': None,
            '3_day': None,
            '5_day': None
        }
    
    # With auto_adjust=True, 'Close' is the adjusted close
    # Handle both single ticker and multi-ticker column formats
    if isinstance(df.columns, pd.MultiIndex):
        # Multi-index columns (ticker in second level)
        prices = df[('Close', ticker)].dropna()
    else:
        # Single index columns
        prices = df['Close'].dropna()
    
    print(f"  Retrieved {len(prices)} trading days")
    print(f"  First date: {prices.index[0].date()}")
    print(f"  Last date: {prices.index[-1].date()}")
    
    # Need at least 6 days (T, T+1, T+2, T+3, T+4, T+5)
    if len(prices) < 6:
        print(f"  ⚠️ Insufficient data: only {len(prices)} days available")
        return {
            '1_day': None,
            '3_day': None,
            '5_day': None
        }
    
    # Get T (pivot) price
    price_T = prices.iloc[0]
    
    # Calculate forward returns
    returns = {}
    
    for days, label in [(1, '1_day'), (3, '3_day'), (5, '5_day')]:
        if len(prices) > days:
            price_forward = prices.iloc[days]
            ret = ((price_forward - price_T) / price_T) * 100
            returns[label] = ret
            print(f"  T+{days}: ${price_T:.2f} → ${price_forward:.2f} = {ret:+.2f}%")
        else:
            returns[label] = None
            print(f"  T+{days}: Insufficient data")
    
    return returns


def main():
    """Calculate forward returns for all cannabis rally endpoints."""
    
    print("=" * 70)
    print("CANNABIS RALLY FORWARD RETURNS ANALYSIS")
    print("=" * 70)
    
    # Define pivot points (end of each rally period)
    tickers_dates = [
        ('TLRY', '2018-12-31'),
        ('CGC', '2018-12-31'),
        ('MSOS', '2021-06-30')
    ]
    
    results = []
    
    for ticker, pivot_date in tickers_dates:
        returns = get_forward_returns(ticker, pivot_date)
        
        results.append({
            'Ticker': ticker,
            'Pivot Date': pivot_date,
            '1-Day Return (%)': returns['1_day'],
            '3-Day Return (%)': returns['3_day'],
            '5-Day Return (%)': returns['5_day']
        })
    
    # Create DataFrame
    df_results = pd.DataFrame(results)
    
    print("\n" + "=" * 70)
    print("FORWARD RETURNS TABLE")
    print("=" * 70)
    print(df_results.to_string(index=False))
    print("=" * 70)
    
    # Save to CSV
    output_file = 'cannabis_forward_returns.csv'
    df_results.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to {output_file}")
    
    # Also save detailed text report
    with open('cannabis_forward_returns.txt', 'w') as f:
        f.write("CANNABIS RALLY FORWARD RETURNS ANALYSIS\n")
        f.write("=" * 70 + "\n\n")
        f.write("Calculation Method:\n")
        f.write("- Used Adjusted Close prices\n")
        f.write("- T = Pivot Date (end of rally period)\n")
        f.write("- 1-Day Return = (Price at T+1 - Price at T) / Price at T × 100%\n")
        f.write("- 3-Day Return = (Price at T+3 - Price at T) / Price at T × 100%\n")
        f.write("- 5-Day Return = (Price at T+5 - Price at T) / Price at T × 100%\n\n")
        f.write("Results:\n")
        f.write("=" * 70 + "\n")
        f.write(df_results.to_string(index=False))
        f.write("\n" + "=" * 70 + "\n")
    
    print(f"✅ Detailed report saved to cannabis_forward_returns.txt")


if __name__ == '__main__':
    main()

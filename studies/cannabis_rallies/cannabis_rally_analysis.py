"""
Cannabis Stock Rally Comparison Analysis
Compares TLRY, CGC (2018) vs MSOS (2021) rallies using quantitative metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Try yfinance first (simpler for historical data)
try:
    import yfinance as yf
    USE_YFINANCE = True
    print("Using yfinance for data retrieval")
except ImportError:
    print("yfinance not installed, installing...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'yfinance'])
    import yfinance as yf
    USE_YFINANCE = True


def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_max_drawdown(close_prices):
    """Calculate maximum drawdown from peak"""
    cumulative = (1 + close_prices.pct_change()).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()
    return max_dd * 100  # Return as percentage


def calculate_rally_metrics(ticker, rally_start, rally_end, lookback_days=100):
    """
    Calculate comprehensive rally metrics for a given ticker and period
    
    Args:
        ticker: Stock ticker symbol
        rally_start: Rally start date (YYYY-MM-DD)
        rally_end: Rally end date (YYYY-MM-DD)
        lookback_days: Days to look back for volume comparison (default 100)
    
    Returns:
        Dictionary of calculated metrics
    """
    print(f"\n{'='*70}")
    print(f"Analyzing {ticker}: {rally_start} to {rally_end}")
    print(f"{'='*70}")
    
    # Calculate lookback start date
    rally_start_dt = pd.to_datetime(rally_start)
    lookback_start_dt = rally_start_dt - timedelta(days=lookback_days + 50)  # Extra buffer for weekends
    
    # Fetch data
    print(f"Fetching data from {lookback_start_dt.date()} to {rally_end}...")
    
    try:
        data = yf.download(ticker, start=lookback_start_dt, end=rally_end, progress=False)
        
        if data.empty:
            print(f"❌ No data available for {ticker}")
            return None
        
        print(f"✓ Retrieved {len(data)} trading days")
        
        # Convert dates to ensure proper filtering
        rally_start_pd = pd.to_datetime(rally_start)
        rally_end_pd = pd.to_datetime(rally_end)
        
        # Split into lookback and rally periods
        rally_data = data[(data.index >= rally_start_pd) & (data.index <= rally_end_pd)].copy()
        
        # Get exactly 100 trading days before rally start
        all_data_before = data[data.index < rally_start_pd].copy()
        if len(all_data_before) > lookback_days:
            lookback_data = all_data_before.iloc[-lookback_days:].copy()
        else:
            lookback_data = all_data_before.copy()
            print(f"⚠️ Only {len(lookback_data)} days available for lookback (requested {lookback_days})")
        
        if rally_data.empty:
            print(f"❌ No data in rally period for {ticker}")
            print(f"   Data range: {data.index.min()} to {data.index.max()}")
            print(f"   Rally range: {rally_start} to {rally_end}")
            return None
        
        print(f"Rally period: {len(rally_data)} trading days")
        print(f"Lookback period: {len(lookback_data)} trading days")
        
        # A. MOMENTUM & VOLATILITY METRICS
        
        # 1. Total Cumulative Return
        start_price = rally_data['Close'].iloc[0]
        end_price = rally_data['Close'].iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100
        
        # 2. Average Daily High-Low Range normalized by 14-period ATR
        rally_data['HL_Range'] = rally_data['High'] - rally_data['Low']
        rally_data['ATR_14'] = calculate_atr(rally_data['High'], rally_data['Low'], rally_data['Close'], period=14)
        
        # Calculate normalized range (skip first 14 days for ATR warmup)
        rally_data['Normalized_Range'] = rally_data['HL_Range'] / rally_data['ATR_14']
        avg_normalized_range = rally_data['Normalized_Range'].iloc[14:].mean()
        
        # 3. Maximum Drawdown
        max_drawdown = calculate_max_drawdown(rally_data['Close'])
        
        # 4. Skewness of Daily Log Returns
        rally_data['Log_Returns'] = np.log(rally_data['Close'] / rally_data['Close'].shift(1))
        skewness = rally_data['Log_Returns'].skew()
        
        # B. PARTICIPATION & LIQUIDITY METRICS
        
        # 1. Average Daily Volume during rally
        avg_daily_volume_rally = rally_data['Volume'].mean()
        
        # 2. Volume Spike Ratio
        avg_daily_volume_lookback = float(lookback_data['Volume'].mean()) if len(lookback_data) > 0 else 0.0
        if avg_daily_volume_lookback > 0:
            volume_spike_ratio = float(avg_daily_volume_rally) / float(avg_daily_volume_lookback)
        else:
            volume_spike_ratio = 0.0
        
        # 3. Days with Extreme Volume (> mean + 2*std from 100-day period)
        if len(lookback_data) > 0:
            lookback_mean = float(lookback_data['Volume'].mean())
            lookback_std = float(lookback_data['Volume'].std())
            extreme_volume_threshold = lookback_mean + (2 * lookback_std)
            extreme_volume_days = int((rally_data['Volume'] > extreme_volume_threshold).sum())
        else:
            extreme_volume_threshold = 0.0
            extreme_volume_days = 0
        
        # Compile results
        metrics = {
            'Ticker': ticker,
            'Rally_Period': f"{rally_start} to {rally_end}",
            'Trading_Days': len(rally_data),
            
            # Momentum & Volatility
            'Total_Return_%': float(total_return),
            'Avg_Normalized_HL_Range': float(avg_normalized_range),
            'Max_Drawdown_%': float(max_drawdown),
            'Log_Returns_Skewness': float(skewness),
            
            # Participation & Liquidity
            'Avg_Daily_Volume_Rally': int(avg_daily_volume_rally),
            'Avg_Daily_Volume_Lookback': int(avg_daily_volume_lookback),
            'Volume_Spike_Ratio': float(volume_spike_ratio),
            'Extreme_Volume_Days': int(extreme_volume_days),
            'Extreme_Volume_Threshold': int(extreme_volume_threshold),
            
            # Price levels
            'Start_Price': float(start_price),
            'End_Price': float(end_price),
            'Peak_Price': float(rally_data['Close'].max()),
        }
        
        # Print summary
        print(f"\n📊 RESULTS for {ticker}:")
        print(f"   Total Return: {float(total_return):+.2f}%")
        print(f"   Max Drawdown: {float(max_drawdown):.2f}%")
        print(f"   Volume Spike Ratio: {float(volume_spike_ratio):.2f}x")
        print(f"   Extreme Volume Days: {int(extreme_volume_days)}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Error fetching/analyzing {ticker}: {e}")
        return None


def main():
    """Main analysis function"""
    print("\n" + "="*70)
    print("CANNABIS STOCK RALLY COMPARISON ANALYSIS")
    print("="*70)
    
    # Define rally periods
    rallies = [
        {'ticker': 'TLRY', 'start': '2018-07-01', 'end': '2018-12-31'},
        {'ticker': 'CGC', 'start': '2018-07-01', 'end': '2018-12-31'},
        {'ticker': 'MSOS', 'start': '2020-10-01', 'end': '2021-06-30'},
    ]
    
    # Calculate metrics for each rally
    results = []
    for rally in rallies:
        metrics = calculate_rally_metrics(
            ticker=rally['ticker'],
            rally_start=rally['start'],
            rally_end=rally['end'],
            lookback_days=100
        )
        if metrics:
            results.append(metrics)
    
    # Create consolidated DataFrame
    if not results:
        print("\n❌ No results to display")
        return
    
    df = pd.DataFrame(results)
    
    # Reorder columns for better presentation
    column_order = [
        'Ticker',
        'Rally_Period',
        'Trading_Days',
        'Start_Price',
        'End_Price',
        'Peak_Price',
        'Total_Return_%',
        'Max_Drawdown_%',
        'Avg_Normalized_HL_Range',
        'Log_Returns_Skewness',
        'Avg_Daily_Volume_Rally',
        'Avg_Daily_Volume_Lookback',
        'Volume_Spike_Ratio',
        'Extreme_Volume_Days',
        'Extreme_Volume_Threshold',
    ]
    
    df = df[column_order]
    
    # Display full results
    print("\n" + "="*70)
    print("CONSOLIDATED RESULTS - CANNABIS RALLY COMPARISON")
    print("="*70 + "\n")
    
    # Set pandas display options for better formatting
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    print(df.to_string(index=False))
    
    # Create comparison summary
    print("\n" + "="*70)
    print("KEY COMPARISONS")
    print("="*70)
    
    # 2018 Rally (TLRY vs CGC)
    print("\n📈 2018 RALLY (July - December):")
    print("-" * 70)
    
    tlry = df[df['Ticker'] == 'TLRY'].iloc[0] if len(df[df['Ticker'] == 'TLRY']) > 0 else None
    cgc = df[df['Ticker'] == 'CGC'].iloc[0] if len(df[df['Ticker'] == 'CGC']) > 0 else None
    
    if tlry is not None and cgc is not None:
        print(f"Total Return:      TLRY {tlry['Total_Return_%']:+.2f}%  vs  CGC {cgc['Total_Return_%']:+.2f}%")
        print(f"Max Drawdown:      TLRY {tlry['Max_Drawdown_%']:.2f}%  vs  CGC {cgc['Max_Drawdown_%']:.2f}%")
        print(f"Volume Spike:      TLRY {tlry['Volume_Spike_Ratio']:.2f}x  vs  CGC {cgc['Volume_Spike_Ratio']:.2f}x")
        print(f"Extreme Vol Days:  TLRY {tlry['Extreme_Volume_Days']}  vs  CGC {cgc['Extreme_Volume_Days']}")
        print(f"Log Return Skew:   TLRY {tlry['Log_Returns_Skewness']:.3f}  vs  CGC {cgc['Log_Returns_Skewness']:.3f}")
    
    # 2021 Rally (MSOS)
    print("\n📈 2021 RALLY (October 2020 - June 2021):")
    print("-" * 70)
    
    msos = df[df['Ticker'] == 'MSOS'].iloc[0] if len(df[df['Ticker'] == 'MSOS']) > 0 else None
    
    if msos is not None:
        print(f"Total Return:      {msos['Total_Return_%']:+.2f}%")
        print(f"Max Drawdown:      {msos['Max_Drawdown_%']:.2f}%")
        print(f"Volume Spike:      {msos['Volume_Spike_Ratio']:.2f}x")
        print(f"Extreme Vol Days:  {msos['Extreme_Volume_Days']}")
        print(f"Log Return Skew:   {msos['Log_Returns_Skewness']:.3f}")
    
    # Cross-period comparison
    print("\n📊 CROSS-PERIOD INSIGHTS:")
    print("-" * 70)
    
    if tlry is not None and cgc is not None and msos is not None:
        avg_2018_return = (tlry['Total_Return_%'] + cgc['Total_Return_%']) / 2
        avg_2018_volume_spike = (tlry['Volume_Spike_Ratio'] + cgc['Volume_Spike_Ratio']) / 2
        
        print(f"Average 2018 Return: {avg_2018_return:+.2f}% vs 2021: {msos['Total_Return_%']:+.2f}%")
        print(f"Average 2018 Vol Spike: {avg_2018_volume_spike:.2f}x vs 2021: {msos['Volume_Spike_Ratio']:.2f}x")
        print(f"\nMost Volatile (Normalized Range): {df['Avg_Normalized_HL_Range'].idxmax()} - {df.loc[df['Avg_Normalized_HL_Range'].idxmax(), 'Ticker']}")
        print(f"Highest Volume Spike: {df.loc[df['Volume_Spike_Ratio'].idxmax(), 'Ticker']} ({df['Volume_Spike_Ratio'].max():.2f}x)")
        print(f"Most Extreme Volume Events: {df.loc[df['Extreme_Volume_Days'].idxmax(), 'Ticker']} ({df['Extreme_Volume_Days'].max()} days)")
    
    # Save to CSV
    output_file = 'cannabis_rally_comparison.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✓ Results saved to: {output_file}")
    
    # Save detailed report
    report_file = 'cannabis_rally_analysis.txt'
    with open(report_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("CANNABIS STOCK RALLY COMPARISON ANALYSIS\n")
        f.write("="*70 + "\n\n")
        f.write("RALLY PERIODS:\n")
        f.write("- 2018 Rally: TLRY & CGC (July 1 - December 31, 2018)\n")
        f.write("- 2021 Rally: MSOS (October 1, 2020 - June 30, 2021)\n\n")
        f.write("="*70 + "\n")
        f.write("CONSOLIDATED METRICS\n")
        f.write("="*70 + "\n\n")
        f.write(df.to_string(index=False))
        f.write("\n\n")
    
    print(f"✓ Detailed report saved to: {report_file}")
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70 + "\n")
    
    return df


if __name__ == "__main__":
    results_df = main()

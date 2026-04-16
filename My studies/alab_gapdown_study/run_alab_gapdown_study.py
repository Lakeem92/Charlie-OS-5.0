"""
ALAB 10%+ Gap Down Study
Analyzes ALAB performance after pre-market gap downs of 10% or more.
Measures day-of, 1-5 day, and 10-20 day forward returns.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from data_router import DataRouter


def calculate_gap_percent(data):
    """
    Calculate gap percentage: (Open - Previous Close) / Previous Close
    """
    data['prev_close'] = data['close'].shift(1)
    data['gap_pct'] = ((data['open'] - data['prev_close']) / data['prev_close']) * 100
    return data


def calculate_forward_returns(data, gap_days_indices):
    """
    Calculate forward returns for gap down events.
    Returns day-of, 1-5 day, and 10-20 day performance metrics.
    """
    results = []
    
    for idx in gap_days_indices:
        event_date = data.loc[idx, 'date']
        gap_pct = data.loc[idx, 'gap_pct']
        open_price = data.loc[idx, 'open']
        close_price = data.loc[idx, 'close']
        
        # Day 0 (day-of) return: close vs open
        day0_return = ((close_price - open_price) / open_price) * 100
        
        result = {
            'date': event_date,
            'gap_pct': gap_pct,
            'open': open_price,
            'close': close_price,
            'day0_return': day0_return,
        }
        
        # Days 1-5 forward returns
        for day in range(1, 6):
            future_idx = idx + day
            if future_idx < len(data):
                future_close = data.iloc[future_idx]['close']
                fwd_return = ((future_close - close_price) / close_price) * 100
                result[f'day{day}_fwd_return'] = fwd_return
            else:
                result[f'day{day}_fwd_return'] = np.nan
        
        # Days 10-20 forward returns
        for day in [10, 15, 20]:
            future_idx = idx + day
            if future_idx < len(data):
                future_close = data.iloc[future_idx]['close']
                fwd_return = ((future_close - close_price) / close_price) * 100
                result[f'day{day}_fwd_return'] = fwd_return
            else:
                result[f'day{day}_fwd_return'] = np.nan
        
        results.append(result)
    
    return pd.DataFrame(results)


def generate_summary_stats(results_df):
    """
    Generate summary statistics for the gap down events.
    """
    summary_lines = []
    summary_lines.append("="*60)
    summary_lines.append("📊 ALAB 10%+ GAP DOWN STUDY - SUMMARY STATISTICS")
    summary_lines.append("="*60)
    summary_lines.append("")
    
    # Event count
    n_events = len(results_df)
    summary_lines.append(f"🔍 Total Gap Down Events (≤-10%): {n_events}")
    summary_lines.append("")
    
    if n_events == 0:
        summary_lines.append("⚠️  No gap down events found in the data period.")
        return "\n".join(summary_lines)
    
    # Date range
    first_event = results_df['date'].min()
    last_event = results_df['date'].max()
    summary_lines.append(f"📅 Event Period: {first_event} to {last_event}")
    summary_lines.append("")
    
    # Gap statistics
    summary_lines.append("📉 GAP DOWN STATISTICS:")
    summary_lines.append(f"   Average Gap: {results_df['gap_pct'].mean():.2f}%")
    summary_lines.append(f"   Largest Gap: {results_df['gap_pct'].min():.2f}%")
    summary_lines.append(f"   Smallest Gap: {results_df['gap_pct'].max():.2f}%")
    summary_lines.append("")
    
    # Day 0 (day-of) performance
    summary_lines.append("📊 DAY 0 (DAY-OF) PERFORMANCE:")
    day0_mean = results_df['day0_return'].mean()
    day0_median = results_df['day0_return'].median()
    day0_wins = (results_df['day0_return'] > 0).sum()
    day0_win_rate = (day0_wins / n_events) * 100
    summary_lines.append(f"   Mean Return: {day0_mean:.2f}%")
    summary_lines.append(f"   Median Return: {day0_median:.2f}%")
    summary_lines.append(f"   Win Rate: {day0_win_rate:.1f}% ({day0_wins}/{n_events})")
    summary_lines.append("")
    
    # Days 1-5 performance
    summary_lines.append("📈 DAYS 1-5 FORWARD RETURNS:")
    for day in range(1, 6):
        col = f'day{day}_fwd_return'
        valid_data = results_df[col].dropna()
        if len(valid_data) > 0:
            mean_ret = valid_data.mean()
            median_ret = valid_data.median()
            wins = (valid_data > 0).sum()
            win_rate = (wins / len(valid_data)) * 100
            summary_lines.append(f"   Day {day}: Mean={mean_ret:+.2f}%, Median={median_ret:+.2f}%, Win Rate={win_rate:.1f}%")
    summary_lines.append("")
    
    # Days 10-20 performance
    summary_lines.append("📊 DAYS 10-20 FORWARD RETURNS:")
    for day in [10, 15, 20]:
        col = f'day{day}_fwd_return'
        valid_data = results_df[col].dropna()
        if len(valid_data) > 0:
            mean_ret = valid_data.mean()
            median_ret = valid_data.median()
            wins = (valid_data > 0).sum()
            win_rate = (wins / len(valid_data)) * 100
            summary_lines.append(f"   Day {day}: Mean={mean_ret:+.2f}%, Median={median_ret:+.2f}%, Win Rate={win_rate:.1f}%")
    summary_lines.append("")
    
    # Best and worst performers
    summary_lines.append("🏆 BEST DAY-OF RECOVERY:")
    best_day = results_df.loc[results_df['day0_return'].idxmax()]
    summary_lines.append(f"   Date: {best_day['date']}, Gap: {best_day['gap_pct']:.2f}%, Recovery: {best_day['day0_return']:.2f}%")
    summary_lines.append("")
    
    summary_lines.append("💥 WORST DAY-OF PERFORMANCE:")
    worst_day = results_df.loc[results_df['day0_return'].idxmin()]
    summary_lines.append(f"   Date: {worst_day['date']}, Gap: {worst_day['gap_pct']:.2f}%, Performance: {worst_day['day0_return']:.2f}%")
    summary_lines.append("")
    
    summary_lines.append("="*60)
    
    return "\n".join(summary_lines)


def main():
    print("🚀 Starting ALAB 10%+ Gap Down Study")
    print("="*60)
    
    # Fetch ALAB daily data
    print("📊 Fetching ALAB daily data...")
    data = DataRouter.get_price_data(
        ticker='ALAB',
        start_date='2020-01-01',  # Get several years of data
        timeframe='daily',
        source='yfinance'  # Use yfinance for reliable data
    )
    
    if data.empty:
        print("❌ No data retrieved for ALAB")
        return
    
    print(f"✅ Retrieved {len(data)} days of data")
    print(f"Date range: {data.index.min()} to {data.index.max()}")
    
    # Handle yfinance MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        # Flatten MultiIndex by taking the first level (OHLCV columns)
        data.columns = data.columns.get_level_values(0)
    
    # Normalize column names to lowercase
    data.columns = data.columns.str.lower()
    
    # Reset index to access dates as a column
    data = data.reset_index()
    
    # Normalize column names to lowercase first
    data.columns = data.columns.str.lower()
    
    # Ensure we have a 'date' column
    if 'timestamp' in data.columns:
        data.rename(columns={'timestamp': 'date'}, inplace=True)
    
    print(f"Columns: {data.columns.tolist()}")
    
    # Calculate gap percentages
    print("\n📉 Calculating gap percentages...")
    data = calculate_gap_percent(data)
    
    # Filter for 10%+ gap downs (gap_pct <= -10)
    gap_down_events = data[data['gap_pct'] <= -10.0].copy()
    
    print(f"✅ Found {len(gap_down_events)} gap down events (≤-10%)")
    
    if len(gap_down_events) == 0:
        print("⚠️  No gap down events found. Study complete.")
        # Save empty results
        output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
        
        with open(os.path.join(output_dir, 'alab_gapdown_summary.txt'), 'w') as f:
            f.write("No gap down events (≤-10%) found for ALAB in the data period.\n")
        
        print(f"\n💾 Saved results to {output_dir}/")
        return
    
    # Get indices of gap down days
    gap_indices = gap_down_events.index.tolist()
    
    # Calculate forward returns
    print("\n📈 Calculating forward returns...")
    results_df = calculate_forward_returns(data, gap_indices)
    
    # Generate summary statistics
    summary_text = generate_summary_stats(results_df)
    print("\n" + summary_text)
    
    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
    
    # Save detailed results CSV
    csv_path = os.path.join(output_dir, 'alab_gapdown_events.csv')
    results_df.to_csv(csv_path, index=False)
    print(f"\n💾 Saved detailed results to {csv_path}")
    
    # Save summary text
    txt_path = os.path.join(output_dir, 'alab_gapdown_summary.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    print(f"💾 Saved summary to {txt_path}")
    
    print("\n✅ Study complete!")


if __name__ == '__main__':
    main()

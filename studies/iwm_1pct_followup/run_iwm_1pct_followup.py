"""
IWM 1% Move Followup Analysis
Analyzes IWM performance the day after a 1%+ move (up or down)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add shared to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from data_router import DataRouter

def main():
    print("🚀 Starting IWM 1% Move Followup Analysis")

    # Get IWM data from 2010 to present
    print("📊 Fetching IWM daily data...")
    data = DataRouter.get_price_data(
        ticker='IWM',
        start_date='2010-01-01',
        timeframe='daily',
        source='yfinance'  # Use yfinance to avoid Alpaca issues
    )

    if data.empty:
        print("❌ No data retrieved")
        return

    print(f"✅ Retrieved {len(data)} days of data")
    print(f"Columns: {data.columns.tolist()}")

    # Handle yfinance MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        close_col = ('Close', 'IWM')
        if close_col not in data.columns:
            print(f"❌ Close column {close_col} not found")
            return
        close_prices = data[close_col]
    else:
        if 'Close' not in data.columns:
            print("❌ Close column not found")
            return
        close_prices = data['Close']

    # Calculate daily returns
    data['daily_return'] = close_prices.pct_change()

    # Find days with 1%+ move (absolute)
    big_move_days = data[abs(data['daily_return']) >= 0.01].copy()

    print(f"📈 Found {len(big_move_days)} days with 1%+ moves")

    # Get next day returns
    followup_returns = []
    for idx in big_move_days.index:
        try:
            next_day = data.index[data.index.get_loc(idx) + 1]
            next_return = data.loc[next_day, 'daily_return']
            followup_returns.append({
                'move_date': idx,
                'move_pct': big_move_days.loc[idx, 'daily_return'] * 100,
                'next_date': next_day,
                'next_return_pct': next_return * 100
            })
        except (KeyError, IndexError):
            # Skip if no next day (end of data)
            continue

    followup_df = pd.DataFrame(followup_returns)

    if followup_df.empty:
        print("❌ No followup data")
        return

    # Drop any rows with NaN or inf next_return_pct
    followup_df = followup_df.dropna(subset=['next_return_pct'])
    followup_df = followup_df[np.isfinite(followup_df['next_return_pct'])]

    if followup_df.empty:
        print("❌ No valid followup data after dropping NaN/inf")
        return

    print(f"📊 Analyzing {len(followup_df)} followup days")

    # Overall stats
    overall_stats = {
        'total_events': len(followup_df),
        'win_rate': np.mean(followup_df['next_return_pct'] > 0) * 100,
        'avg_next_move': followup_df['next_return_pct'].mean(),
        'median_next_move': followup_df['next_return_pct'].median(),
        'std_next_move': followup_df['next_return_pct'].std(),
        'max_next_move': followup_df['next_return_pct'].max(),
        'min_next_move': followup_df['next_return_pct'].min(),
        'positive_moves': np.sum(followup_df['next_return_pct'] > 0),
        'negative_moves': np.sum(followup_df['next_return_pct'] < 0)
    }

    # Separate by up vs down moves
    up_moves = followup_df[followup_df['move_pct'] > 0]
    down_moves = followup_df[followup_df['move_pct'] < 0]

    up_stats = {
        'total_up_moves': len(up_moves),
        'up_win_rate': np.mean(up_moves['next_return_pct'] > 0) * 100 if not up_moves.empty else 0,
        'up_avg_next': up_moves['next_return_pct'].mean() if not up_moves.empty else 0
    }

    down_stats = {
        'total_down_moves': len(down_moves),
        'down_win_rate': np.mean(down_moves['next_return_pct'] > 0) * 100 if not down_moves.empty else 0,
        'down_avg_next': down_moves['next_return_pct'].mean() if not down_moves.empty else 0
    }

    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), 'outputs')

    # Save detailed CSV
    followup_df.to_csv(os.path.join(output_dir, 'iwm_1pct_followup_details.csv'), index=False)

    # Save summary text
    with open(os.path.join(output_dir, 'iwm_1pct_followup_summary.txt'), 'w') as f:
        f.write("IWM 1%+ Move Followup Analysis Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Analysis Period: 2010-01-01 to {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"Total 1%+ Move Days: {overall_stats['total_events']}\n\n")

        f.write("OVERALL FOLLOWUP PERFORMANCE:\n")
        f.write(f"Win Rate: {overall_stats['win_rate']:.1f}%\n")
        f.write(f"Average Next Day Move: {overall_stats['avg_next_move']:.2f}%\n")
        f.write(f"Median Next Day Move: {overall_stats['median_next_move']:.2f}%\n")
        f.write(f"Std Dev Next Day Move: {overall_stats['std_next_move']:.2f}%\n")
        f.write(f"Max Next Day Move: {overall_stats['max_next_move']:.2f}%\n")
        f.write(f"Min Next Day Move: {overall_stats['min_next_move']:.2f}%\n")
        f.write(f"Positive Followup Days: {overall_stats['positive_moves']}\n")
        f.write(f"Negative Followup Days: {overall_stats['negative_moves']}\n\n")

        f.write("AFTER UP MOVES (>=1%):\n")
        f.write(f"Total Up Move Events: {up_stats['total_up_moves']}\n")
        f.write(f"Win Rate: {up_stats['up_win_rate']:.1f}%\n")
        f.write(f"Average Next Day Move: {up_stats['up_avg_next']:.2f}%\n\n")

        f.write("AFTER DOWN MOVES (<= -1%):\n")
        f.write(f"Total Down Move Events: {down_stats['total_down_moves']}\n")
        f.write(f"Win Rate: {down_stats['down_win_rate']:.1f}%\n")
        f.write(f"Average Next Day Move: {down_stats['down_avg_next']:.2f}%\n\n")

        f.write("💡 Key Insights:\n")
        if overall_stats['win_rate'] > 50:
            f.write("- Next day tends to be positive after big moves\n")
        else:
            f.write("- Next day tends to be negative after big moves\n")

        if abs(overall_stats['avg_next_move']) > 0.5:
            f.write("- Significant average movement the next day\n")
        else:
            f.write("- Relatively modest average movement the next day\n")

    print("✅ Analysis complete! Results saved to outputs/ folder")
    print(f"📄 Summary: Win rate {overall_stats['win_rate']:.1f}%, Avg next move {overall_stats['avg_next_move']:.2f}%")

if __name__ == "__main__":
    main()
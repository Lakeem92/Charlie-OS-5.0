"""
Prediction Market Event Study
=============================

This study analyzes forward stock returns following significant shifts
in prediction market odds.

EDIT THE PARAMETERS BELOW, then run:
    python run_study.py

Outputs saved to outputs/ folder.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add tools to path for pm_data_loader import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "prediction_markets"))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pm_data_loader import (
    search_markets,
    detect_odds_events,
    run_event_study,
    list_available_data
)

# ============================================================
# ==================== EDIT PARAMETERS HERE ==================
# ============================================================

# Step 1: Find your market
# Run this first to search for markets:
#   results = search_markets("federal reserve", source="kalshi")
#   print(results[['market_id', 'title', 'volume']])
# Then copy the market_id below.

MARKET_SEARCH_KEYWORD = "federal reserve"  # EDIT: Your search term
MARKET_ID = ""                              # EDIT: Paste market_id from search results
SOURCE = "kalshi"                           # EDIT: "polymarket" or "kalshi"

# Step 2: What stock to analyze?
TICKER = "QQQ"                              # EDIT: Stock/ETF ticker

# Step 3: Event detection parameters
THRESHOLD_ABS = 0.10                        # Minimum probability change (0.10 = 10%)
WINDOW_DAYS = 7                             # Days over which to measure change
FORWARD_DAYS = [1, 2, 3, 5, 10]             # Forward return horizons

# Step 4: Direction labels (optional customization)
# For Fed markets: {"up": "HAWKISH", "down": "DOVISH"}
# For general: {"up": "BULLISH", "down": "BEARISH"}
DIRECTION_LABELS = None  # Use default, or set custom dict

# ============================================================
# ==================== END OF PARAMETERS =====================
# ============================================================

# Output paths
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def find_market():
    """Helper function to search for markets."""
    print(f"\n🔍 Searching for markets matching: '{MARKET_SEARCH_KEYWORD}'")
    print(f"   Source: {SOURCE}\n")
    
    results = search_markets(MARKET_SEARCH_KEYWORD, source=SOURCE, limit=20)
    
    if results.empty:
        print("❌ No markets found. Try a different keyword.")
        return
    
    print("Found markets:")
    print("=" * 80)
    
    display_cols = ['market_id', 'title', 'volume', 'status']
    available_cols = [c for c in display_cols if c in results.columns]
    
    for i, row in results.iterrows():
        print(f"\n[{i+1}] {row.get('title', row.get('market_id', 'Unknown'))}")
        print(f"    ID: {row.get('market_id', 'N/A')}")
        print(f"    Volume: ${row.get('volume', 0):,.0f}")
        print(f"    Status: {row.get('status', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("Copy the market_id and paste it into MARKET_ID in this script.")


def run_study_main():
    """Run the full event study."""
    
    # Check for market_id
    if not MARKET_ID:
        print("⚠️  MARKET_ID not set!")
        print("   Run find_market() first, or set MARKET_ID manually.")
        print("\n   Example: Uncomment the line below and run again:")
        print("   # find_market()")
        return
    
    print("=" * 60)
    print("PREDICTION MARKET EVENT STUDY")
    print("=" * 60)
    print(f"Market ID: {MARKET_ID}")
    print(f"Source: {SOURCE}")
    print(f"Ticker: {TICKER}")
    print(f"Threshold: {THRESHOLD_ABS * 100:.0f}% probability change")
    print(f"Window: {WINDOW_DAYS} days")
    print(f"Forward horizons: {FORWARD_DAYS}")
    print()
    
    # Run the study
    print("📊 Running event study...")
    events_df, summary = run_event_study(
        market_id=MARKET_ID,
        ticker=TICKER,
        threshold_abs=THRESHOLD_ABS,
        window_days=WINDOW_DAYS,
        forward_days=FORWARD_DAYS,
        source=SOURCE,
        direction_labels=DIRECTION_LABELS
    )
    
    n_events = summary.get('n_events', 0)
    print(f"   Found {n_events} events")
    
    if n_events == 0:
        print("❌ No events found. Try lowering THRESHOLD_ABS or changing WINDOW_DAYS.")
        return
    
    # Save raw results
    results_path = OUTPUT_DIR / "results.csv"
    events_df.to_csv(results_path, index=False)
    print(f"\n💾 Raw results saved to: {results_path}")
    
    # Save summary stats
    summary_path = OUTPUT_DIR / "summary_stats.txt"
    with open(summary_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("PREDICTION MARKET EVENT STUDY - SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Market ID: {MARKET_ID}\n")
        f.write(f"Source: {SOURCE}\n")
        f.write(f"Ticker: {TICKER}\n")
        f.write(f"Threshold: {THRESHOLD_ABS * 100:.0f}%\n")
        f.write(f"Window: {WINDOW_DAYS} days\n")
        f.write(f"Events Found: {n_events}\n\n")
        
        f.write("FORWARD RETURN STATISTICS\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Horizon':<10} {'N':<6} {'Win Rate':<10} {'Mean':<10} {'Median':<10} {'t-stat':<10} {'p-value':<10}\n")
        f.write("-" * 60 + "\n")
        
        for days in FORWARD_DAYS:
            col = f'fwd_{days}d'
            if col in summary:
                s = summary[col]
                f.write(f"{days}-day{'':<5} ")
                f.write(f"{s.get('n', 0):<6} ")
                f.write(f"{s.get('win_rate', 0)*100:>6.1f}%   ")
                f.write(f"{s.get('mean', 0)*100:>+7.2f}%  ")
                f.write(f"{s.get('median', 0)*100:>+7.2f}%  ")
                f.write(f"{s.get('t_stat', np.nan):>8.2f}  ")
                f.write(f"{s.get('p_value', np.nan):>8.4f}\n")
        
        # Significance check
        f.write("\n" + "-" * 60 + "\n")
        for days in FORWARD_DAYS:
            col = f'fwd_{days}d'
            if col in summary:
                p = summary[col].get('p_value', 1)
                if p < 0.05:
                    f.write(f"✅ {days}-day return: SIGNIFICANT at 5% level (p={p:.4f})\n")
                elif p < 0.10:
                    f.write(f"⚠️ {days}-day return: Marginally significant (p={p:.4f})\n")
    
    print(f"💾 Summary saved to: {summary_path}")
    
    # Generate chart
    try:
        chart_path = OUTPUT_DIR / "forward_returns.png"
        
        fig, axes = plt.subplots(1, len(FORWARD_DAYS), figsize=(4 * len(FORWARD_DAYS), 4))
        if len(FORWARD_DAYS) == 1:
            axes = [axes]
        
        for i, days in enumerate(FORWARD_DAYS):
            col = f'fwd_{days}d'
            returns = events_df[col].dropna() * 100  # Convert to percentage
            
            if len(returns) > 0:
                axes[i].hist(returns, bins=min(20, len(returns)), edgecolor='black', alpha=0.7)
                axes[i].axvline(0, color='red', linestyle='--', linewidth=2)
                axes[i].axvline(returns.mean(), color='green', linestyle='-', linewidth=2, label=f'Mean: {returns.mean():.2f}%')
                axes[i].set_xlabel('Return (%)')
                axes[i].set_ylabel('Frequency')
                axes[i].set_title(f'{days}-Day Forward Return\nN={len(returns)}, WR={summary[col]["win_rate"]*100:.0f}%')
                axes[i].legend()
        
        plt.suptitle(f'{TICKER} Returns After {THRESHOLD_ABS*100:.0f}%+ Odds Shift ({MARKET_ID})', y=1.02)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Chart saved to: {chart_path}")
        
    except Exception as e:
        print(f"⚠️ Chart generation failed: {e}")
    
    # Print summary to console
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for days in FORWARD_DAYS:
        col = f'fwd_{days}d'
        if col in summary:
            s = summary[col]
            sig = "✅" if s.get('p_value', 1) < 0.05 else "❌"
            print(f"{days}-day: WR={s.get('win_rate',0)*100:.0f}%, Mean={s.get('mean',0)*100:+.2f}%, p={s.get('p_value',1):.3f} {sig}")
    
    print("\n✅ Study complete! Check outputs/ folder for results.")


if __name__ == "__main__":
    # Check data availability first
    status = list_available_data()
    
    if not status['polymarket']['available'] and not status['kalshi']['available']:
        print("❌ Prediction market data not found!")
        print(f"   Run 'make setup' in: {Path(__file__).parent.parent.parent / 'tools' / 'prediction_markets'}")
        sys.exit(1)
    
    # Uncomment ONE of the lines below:
    
    # Option 1: Search for markets (run this first)
    # find_market()
    
    # Option 2: Run the study (after setting MARKET_ID)
    run_study_main()

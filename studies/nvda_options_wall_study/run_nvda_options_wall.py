"""
╔══════════════════════════════════════════════════════════════════════╗
║  QUANTLAB STUDY: NVDA POST-EARNINGS OPTIONS WALL BEHAVIOR          ║
║  Date: February 26, 2026                                          ║
║  Hypothesis: When NVDA's post-earnings move CLEARS the nearest     ║
║  major call strike above the pre-earnings close, the gap holds     ║
║  and continuation is more likely. When it FAILS to clear, the      ║
║  gap fades.                                                        ║
╚══════════════════════════════════════════════════════════════════════╝

METHODOLOGY:
1. For each of NVDA's last 12 earnings dates:
   a. Pull the closing price the day BEFORE earnings ("pre-earnings level")
   b. Pull the next day's open, high, close as proxy for AH/gap reaction
   c. Identify nearest major call strike ABOVE the pre-earnings close
      ($5 increments if price < $200, $10 increments if price >= $200)
   d. Determine if AH move CLEARED that strike (close > strike * 1.01)
2. Split events into CLEARED vs NOT CLEARED buckets
3. Calculate per-bucket: avg next-day return (O→C), avg 3-day return, win rates
4. Chart forward return distributions for both buckets
5. Save summary table + charts to outputs/

NOTE ON DATA:
- Alpaca IEX feed does not provide extended-hours bars.
- We use the next trading day's open as the post-earnings reaction price
  (it captures the overnight gap from earnings) and the next day's high
  as the max upside reached. "Cleared" is based on next-day CLOSE vs strike.
"""

import sys
import os

sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from shared.data_router import DataRouter

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

TICKER = "NVDA"
STUDY_NAME = "nvda_options_wall_study"
STUDY_DIR = Path(r'C:\QuantLab\Data_Lab\studies') / STUDY_NAME
OUTPUT_DIR = STUDY_DIR / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"

for d in [STUDY_DIR, OUTPUT_DIR, CHARTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# NVDA earnings dates (after-market close reports).
# These are the dates NVDA REPORTED earnings (after close).
# The "pre-earnings close" is the closing price ON this date.
# The "post-earnings reaction" shows up the NEXT trading day.
#
# NOTE: NVDA did a 10-for-1 stock split effective June 10, 2024.
# Alpaca returns split-adjusted data, so prices are comparable.

EARNINGS_DATES = [
    "2025-11-19",  # Q3 FY2026
    "2025-08-27",  # Q2 FY2026
    "2025-05-28",  # Q1 FY2026
    "2025-02-26",  # Q4 FY2025
    "2024-11-20",  # Q3 FY2025
    "2024-08-28",  # Q2 FY2025
    "2024-05-22",  # Q1 FY2025
    "2024-02-21",  # Q4 FY2024
    "2023-11-21",  # Q3 FY2024
    "2023-08-23",  # Q2 FY2024
    "2023-05-24",  # Q1 FY2024
    "2023-02-22",  # Q4 FY2023
]

# Minimum gap threshold to validate an earnings date (post-split adjusted)
MIN_EARNINGS_GAP_PCT = 0.02  # 2% gap confirms it was likely an earnings day

# "Cleared" definition: next-day close > strike * (1 + CLEAR_THRESHOLD)
CLEAR_THRESHOLD = 0.01  # 1% above the call wall strike

# Forward return windows in trading days
FWD_WINDOWS = {"1d": 1, "3d": 3}

DATA_START = "2022-12-01"  # Buffer before earliest earnings date
DATA_END = "2026-02-26"


# ═══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def nearest_call_strike_above(price: float) -> tuple[float, int]:
    """
    Find the nearest major call strike ABOVE the given price.
    Uses $10 increments if price >= $200, else $5.
    Returns (strike, increment_used).
    """
    increment = 10 if price >= 200 else 5
    strike = np.ceil(price / increment) * increment
    # If price is exactly on the strike, go up one increment
    if strike == price:
        strike += increment
    return float(strike), increment


def get_trading_day_offset(df: pd.DataFrame, date: str, offset: int) -> pd.Timestamp:
    """
    Given a DataFrame indexed by trading dates and a reference date string,
    return the trading date that is `offset` trading days away.
    offset=0 returns the date itself (or nearest), offset=1 is next day, etc.
    """
    idx = df.index
    # Find the position of the reference date or the nearest date after it
    ref_date = pd.Timestamp(date)
    mask = idx >= ref_date
    if not mask.any():
        return None
    first_pos = np.argmax(mask)
    target_pos = first_pos + offset
    if target_pos < 0 or target_pos >= len(idx):
        return None
    return idx[target_pos]


def safe_loc(df: pd.DataFrame, date: pd.Timestamp, col: str):
    """Safely get a value from the DataFrame."""
    try:
        return float(df.loc[date, col])
    except (KeyError, TypeError):
        return np.nan


# ═══════════════════════════════════════════════════════
# PHASE 1: DATA COLLECTION
# ═══════════════════════════════════════════════════════

print("=" * 70)
print(f"  NVDA POST-EARNINGS OPTIONS WALL STUDY")
print("=" * 70)
print(f"  Ticker:          {TICKER}")
print(f"  Earnings events: {len(EARNINGS_DATES)}")
print(f"  Data range:      {DATA_START} → {DATA_END}")
print(f"  Clear threshold: >{CLEAR_THRESHOLD*100:.0f}% above call strike")
print()

print("PHASE 1: Pulling NVDA daily price data via Alpaca...")
print("-" * 50)

try:
    nvda_df = DataRouter.get_price_data(
        ticker=TICKER,
        start_date=DATA_START,
        end_date=DATA_END,
        timeframe='daily',
        source='alpaca',
        fallback=True,
        study_type='returns'
    )
    nvda_df = nvda_df.sort_index()
    # Normalize index to date-only (no timezone) for clean matching
    if hasattr(nvda_df.index, 'tz') and nvda_df.index.tz is not None:
        nvda_df.index = nvda_df.index.tz_convert('US/Eastern').normalize().tz_localize(None)
    else:
        nvda_df.index = pd.to_datetime(nvda_df.index).normalize()
    # Remove any duplicate index entries
    nvda_df = nvda_df[~nvda_df.index.duplicated(keep='first')]
    print(f"  ✅ {TICKER}: {len(nvda_df)} daily bars loaded")
    print(f"     Date range: {nvda_df.index[0].strftime('%Y-%m-%d')} to {nvda_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"     Price range: ${nvda_df['Close'].min():.2f} — ${nvda_df['Close'].max():.2f}")
except Exception as e:
    print(f"  ❌ CRITICAL: Failed to load {TICKER} data: {e}")
    raise SystemExit(1)

# Save raw data
nvda_df.to_csv(OUTPUT_DIR / "nvda_daily_data.csv")
print(f"  💾 Raw data saved → outputs/nvda_daily_data.csv")
print()


# ═══════════════════════════════════════════════════════
# PHASE 2: EVENT ANALYSIS
# ═══════════════════════════════════════════════════════

print("PHASE 2: Analyzing each earnings event...")
print("-" * 50)

events = []

for earn_date_str in EARNINGS_DATES:
    earn_date = pd.Timestamp(earn_date_str)
    
    # --- Pre-earnings close: the closing price ON earnings day ---
    # (NVDA reports after market close, so the close on this date
    #  is the last price BEFORE the earnings announcement)
    pre_earn_day = get_trading_day_offset(nvda_df, earn_date_str, 0)
    
    if pre_earn_day is None:
        # Maybe the exact date isn't a trading day; try finding the nearest before
        mask = nvda_df.index <= earn_date
        if not mask.any():
            print(f"  ⚠️  {earn_date_str}: No data at/before this date — skipping")
            continue
        pre_earn_day = nvda_df.index[mask][-1]
    
    pre_close = safe_loc(nvda_df, pre_earn_day, 'Close')
    if np.isnan(pre_close):
        print(f"  ⚠️  {earn_date_str}: No close data on {pre_earn_day.strftime('%Y-%m-%d')} — skipping")
        continue
    
    # --- Post-earnings day (T+1): the next trading day ---
    next_day = get_trading_day_offset(nvda_df, pre_earn_day.strftime('%Y-%m-%d'), 1)
    if next_day is None:
        print(f"  ⚠️  {earn_date_str}: No next trading day data — skipping")
        continue
    
    next_open = safe_loc(nvda_df, next_day, 'Open')
    next_high = safe_loc(nvda_df, next_day, 'High')
    next_close = safe_loc(nvda_df, next_day, 'Close')
    next_low = safe_loc(nvda_df, next_day, 'Low')
    
    if any(np.isnan(x) for x in [next_open, next_high, next_close]):
        print(f"  ⚠️  {earn_date_str}: Incomplete next-day data — skipping")
        continue
    
    # Validate earnings gap
    gap_pct = (next_open - pre_close) / pre_close
    
    # --- Nearest call strike above pre-earnings close ---
    strike, increment = nearest_call_strike_above(pre_close)
    distance_to_strike = (strike - pre_close) / pre_close
    
    # --- Did the move CLEAR the strike? ---
    # "Cleared" = next-day close > strike * 1.01
    clear_level = strike * (1 + CLEAR_THRESHOLD)
    cleared = next_close > clear_level
    
    # Also check: did the HIGH reach the strike (even if close didn't hold)?
    high_reached_strike = next_high >= strike
    
    # --- Forward returns ---
    # Next-day return: Open → Close on post-earnings day
    next_day_return_oc = (next_close - next_open) / next_open
    
    # 3-day forward return: post-earnings open → close 3 trading days later
    day3 = get_trading_day_offset(nvda_df, next_day.strftime('%Y-%m-%d'), 2)  # +2 from next_day = 3rd trading day
    if day3 is not None:
        day3_close = safe_loc(nvda_df, day3, 'Close')
        fwd_3d_return = (day3_close - next_open) / next_open if not np.isnan(day3_close) else np.nan
    else:
        day3_close = np.nan
        fwd_3d_return = np.nan
    
    # 1-day forward return: close-to-close (pre_close → next_close)
    fwd_1d_return_cc = (next_close - pre_close) / pre_close
    
    event = {
        'earnings_date': earn_date_str,
        'pre_earn_day': pre_earn_day.strftime('%Y-%m-%d'),
        'pre_close': round(pre_close, 2),
        'next_day': next_day.strftime('%Y-%m-%d'),
        'next_open': round(next_open, 2),
        'next_high': round(next_high, 2),
        'next_low': round(next_low, 2),
        'next_close': round(next_close, 2),
        'gap_pct': round(gap_pct * 100, 2),
        'strike': strike,
        'strike_increment': increment,
        'distance_to_strike_pct': round(distance_to_strike * 100, 2),
        'clear_level': round(clear_level, 2),
        'cleared': cleared,
        'high_reached_strike': high_reached_strike,
        'next_day_return_oc_pct': round(next_day_return_oc * 100, 2),
        'fwd_1d_return_cc_pct': round(fwd_1d_return_cc * 100, 2),
        'fwd_3d_return_pct': round(fwd_3d_return * 100, 2) if not np.isnan(fwd_3d_return) else np.nan,
    }
    events.append(event)
    
    status = "✅ CLEARED" if cleared else "❌ NOT CLEARED"
    print(f"  {earn_date_str} | Pre: ${pre_close:>8.2f} | Strike: ${strike:>8.0f} (${increment}) "
          f"| Gap: {gap_pct*100:>+6.1f}% | Next Close: ${next_close:>8.2f} | {status}")

print()
print(f"  Total events analyzed: {len(events)}")

if len(events) == 0:
    print("  ❌ No valid events — check earnings dates or data availability.")
    raise SystemExit(1)

events_df = pd.DataFrame(events)


# ═══════════════════════════════════════════════════════
# PHASE 3: BUCKET ANALYSIS
# ═══════════════════════════════════════════════════════

print()
print("PHASE 3: Bucket analysis — CLEARED vs NOT CLEARED")
print("-" * 50)

cleared_df = events_df[events_df['cleared'] == True].copy()
not_cleared_df = events_df[events_df['cleared'] == False].copy()

print(f"  🟢 CLEARED bucket:      {len(cleared_df)} events")
print(f"  🔴 NOT CLEARED bucket:  {len(not_cleared_df)} events")
print()


def bucket_stats(df: pd.DataFrame, label: str) -> dict:
    """Calculate summary statistics for a bucket."""
    n = len(df)
    if n == 0:
        return {
            'label': label,
            'count': 0,
            'avg_gap_pct': np.nan,
            'avg_next_day_oc': np.nan,
            'avg_fwd_3d': np.nan,
            'win_rate_1d': np.nan,
            'win_rate_3d': np.nan,
            'median_next_day_oc': np.nan,
            'median_fwd_3d': np.nan,
            'best_next_day': np.nan,
            'worst_next_day': np.nan,
        }
    
    # Filter NaN for 3d returns
    valid_3d = df['fwd_3d_return_pct'].dropna()
    
    return {
        'label': label,
        'count': n,
        'avg_gap_pct': round(df['gap_pct'].mean(), 2),
        'avg_next_day_oc': round(df['next_day_return_oc_pct'].mean(), 2),
        'avg_fwd_3d': round(valid_3d.mean(), 2) if len(valid_3d) > 0 else np.nan,
        'win_rate_1d': round((df['next_day_return_oc_pct'] > 0).mean() * 100, 1),
        'win_rate_3d': round((valid_3d > 0).mean() * 100, 1) if len(valid_3d) > 0 else np.nan,
        'median_next_day_oc': round(df['next_day_return_oc_pct'].median(), 2),
        'median_fwd_3d': round(valid_3d.median(), 2) if len(valid_3d) > 0 else np.nan,
        'best_next_day': round(df['next_day_return_oc_pct'].max(), 2),
        'worst_next_day': round(df['next_day_return_oc_pct'].min(), 2),
    }


cleared_stats = bucket_stats(cleared_df, "CLEARED")
not_cleared_stats = bucket_stats(not_cleared_df, "NOT CLEARED")

# Print bucket comparison
print("  ┌────────────────────────┬──────────────┬──────────────┐")
print("  │ Metric                 │   CLEARED    │ NOT CLEARED  │")
print("  ├────────────────────────┼──────────────┼──────────────┤")
print(f"  │ Event Count            │ {cleared_stats['count']:>12} │ {not_cleared_stats['count']:>12} │")
print(f"  │ Avg Gap %              │ {cleared_stats['avg_gap_pct']:>+11.2f}% │ {not_cleared_stats['avg_gap_pct']:>+11.2f}% │")
print(f"  │ Avg Next-Day O→C %     │ {cleared_stats['avg_next_day_oc']:>+11.2f}% │ {not_cleared_stats['avg_next_day_oc']:>+11.2f}% │")
print(f"  │ Med Next-Day O→C %     │ {cleared_stats['median_next_day_oc']:>+11.2f}% │ {not_cleared_stats['median_next_day_oc']:>+11.2f}% │")
print(f"  │ Avg 3-Day Fwd %        │ {cleared_stats['avg_fwd_3d']:>+11.2f}% │ {not_cleared_stats['avg_fwd_3d']:>+11.2f}% │")
print(f"  │ Med 3-Day Fwd %        │ {cleared_stats['median_fwd_3d']:>+11.2f}% │ {not_cleared_stats['median_fwd_3d']:>+11.2f}% │")
print(f"  │ Win Rate 1d            │ {cleared_stats['win_rate_1d']:>11.1f}% │ {not_cleared_stats['win_rate_1d']:>11.1f}% │")
print(f"  │ Win Rate 3d            │ {cleared_stats['win_rate_3d']:>11.1f}% │ {not_cleared_stats['win_rate_3d']:>11.1f}% │")
print(f"  │ Best Next-Day O→C %    │ {cleared_stats['best_next_day']:>+11.2f}% │ {not_cleared_stats['best_next_day']:>+11.2f}% │")
print(f"  │ Worst Next-Day O→C %   │ {cleared_stats['worst_next_day']:>+11.2f}% │ {not_cleared_stats['worst_next_day']:>+11.2f}% │")
print("  └────────────────────────┴──────────────┴──────────────┘")
print()


# ═══════════════════════════════════════════════════════
# PHASE 4: FULL EVENT TABLE
# ═══════════════════════════════════════════════════════

print("PHASE 4: Full event summary table")
print("-" * 50)

print()
print(f"  {'Date':<12} {'Pre-Close':>10} {'Strike':>8} {'Gap%':>7} {'NxtClose':>10} "
      f"{'Cleared':>8} {'O→C%':>7} {'3d Fwd%':>8}")
print(f"  {'─'*12} {'─'*10} {'─'*8} {'─'*7} {'─'*10} {'─'*8} {'─'*7} {'─'*8}")

for _, row in events_df.iterrows():
    bucket_flag = "🟢 YES" if row['cleared'] else "🔴 NO"
    fwd3 = f"{row['fwd_3d_return_pct']:>+7.2f}%" if not pd.isna(row['fwd_3d_return_pct']) else "    N/A"
    print(f"  {row['earnings_date']:<12} ${row['pre_close']:>8.2f} ${row['strike']:>6.0f} "
          f"{row['gap_pct']:>+6.1f}% ${row['next_close']:>8.2f} "
          f"{bucket_flag:>8} {row['next_day_return_oc_pct']:>+6.2f}% {fwd3}")

print()


# ═══════════════════════════════════════════════════════
# PHASE 5: CHARTS
# ═══════════════════════════════════════════════════════

print("PHASE 5: Generating charts...")
print("-" * 50)


# ── Chart 1: Forward Returns Comparison (Grouped Bar) ──

def build_forward_returns_chart():
    """Grouped bar chart: CLEARED vs NOT CLEARED avg returns."""
    
    metrics = ['Avg Next-Day O→C', 'Med Next-Day O→C', 'Avg 3-Day Fwd', 'Med 3-Day Fwd']
    cleared_vals = [
        cleared_stats['avg_next_day_oc'],
        cleared_stats['median_next_day_oc'],
        cleared_stats['avg_fwd_3d'],
        cleared_stats['median_fwd_3d'],
    ]
    not_cleared_vals = [
        not_cleared_stats['avg_next_day_oc'],
        not_cleared_stats['median_next_day_oc'],
        not_cleared_stats['avg_fwd_3d'],
        not_cleared_stats['median_fwd_3d'],
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name=f"CLEARED (n={cleared_stats['count']})",
        x=metrics,
        y=cleared_vals,
        marker_color='#26a69a',
        text=[f"{v:+.2f}%" if not np.isnan(v) else "N/A" for v in cleared_vals],
        textposition='outside',
    ))
    
    fig.add_trace(go.Bar(
        name=f"NOT CLEARED (n={not_cleared_stats['count']})",
        x=metrics,
        y=not_cleared_vals,
        marker_color='#ef5350',
        text=[f"{v:+.2f}%" if not np.isnan(v) else "N/A" for v in not_cleared_vals],
        textposition='outside',
    ))
    
    fig.add_hline(y=0, line_dash="dot", line_color="white", line_width=0.8)
    
    fig.update_layout(
        template="plotly_dark",
        title=f"NVDA Post-Earnings: Call Wall CLEARED vs NOT CLEARED — Forward Returns",
        barmode="group",
        xaxis_title="Metric",
        yaxis_title="Return (%)",
        height=550,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
    )
    
    save_path = CHARTS_DIR / "forward_returns_comparison.html"
    fig.write_html(str(save_path))
    print(f"  💾 Chart 1 saved → charts/forward_returns_comparison.html")
    return fig


# ── Chart 2: Win Rate Comparison ──

def build_winrate_chart():
    """Side-by-side win rate bars."""
    
    horizons = ['1-Day Win Rate', '3-Day Win Rate']
    cleared_vals = [cleared_stats['win_rate_1d'], cleared_stats['win_rate_3d']]
    not_cleared_vals = [not_cleared_stats['win_rate_1d'], not_cleared_stats['win_rate_3d']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name=f"CLEARED (n={cleared_stats['count']})",
        x=horizons,
        y=cleared_vals,
        marker_color='#26a69a',
        text=[f"{v:.0f}%" if not np.isnan(v) else "N/A" for v in cleared_vals],
        textposition='outside',
    ))
    
    fig.add_trace(go.Bar(
        name=f"NOT CLEARED (n={not_cleared_stats['count']})",
        x=horizons,
        y=not_cleared_vals,
        marker_color='#ef5350',
        text=[f"{v:.0f}%" if not np.isnan(v) else "N/A" for v in not_cleared_vals],
        textposition='outside',
    ))
    
    fig.add_hline(y=50, line_dash="dash", line_color="yellow", line_width=0.8,
                  annotation_text="50% baseline", annotation_position="top right")
    
    fig.update_layout(
        template="plotly_dark",
        title="NVDA Post-Earnings: Win Rate by Bucket",
        barmode="group",
        xaxis_title="Horizon",
        yaxis_title="Win Rate (%)",
        yaxis_range=[0, 105],
        height=500,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
    )
    
    save_path = CHARTS_DIR / "winrate_comparison.html"
    fig.write_html(str(save_path))
    print(f"  💾 Chart 2 saved → charts/winrate_comparison.html")
    return fig


# ── Chart 3: Individual Event Returns Distribution (Strip/Box) ──

def build_distribution_chart():
    """Box + strip plot showing return distributions for each bucket."""
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Next-Day Return (Open→Close)", "3-Day Forward Return"],
        horizontal_spacing=0.15,
    )
    
    # --- Next-Day O→C ---
    if len(cleared_df) > 0:
        fig.add_trace(go.Box(
            y=cleared_df['next_day_return_oc_pct'],
            name="CLEARED",
            marker_color='#26a69a',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.5,
            showlegend=True,
            legendgroup="cleared",
        ), row=1, col=1)
    
    if len(not_cleared_df) > 0:
        fig.add_trace(go.Box(
            y=not_cleared_df['next_day_return_oc_pct'],
            name="NOT CLEARED",
            marker_color='#ef5350',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.5,
            showlegend=True,
            legendgroup="not_cleared",
        ), row=1, col=1)
    
    # --- 3-Day Forward ---
    cleared_3d = cleared_df['fwd_3d_return_pct'].dropna()
    not_cleared_3d = not_cleared_df['fwd_3d_return_pct'].dropna()
    
    if len(cleared_3d) > 0:
        fig.add_trace(go.Box(
            y=cleared_3d,
            name="CLEARED",
            marker_color='#26a69a',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.5,
            showlegend=False,
            legendgroup="cleared",
        ), row=1, col=2)
    
    if len(not_cleared_3d) > 0:
        fig.add_trace(go.Box(
            y=not_cleared_3d,
            name="NOT CLEARED",
            marker_color='#ef5350',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.5,
            showlegend=False,
            legendgroup="not_cleared",
        ), row=1, col=2)
    
    fig.add_hline(y=0, line_dash="dot", line_color="white", line_width=0.8, row=1, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="white", line_width=0.8, row=1, col=2)
    
    fig.update_yaxes(title_text="Return (%)", row=1, col=1)
    fig.update_yaxes(title_text="Return (%)", row=1, col=2)
    
    fig.update_layout(
        template="plotly_dark",
        title="NVDA Post-Earnings Return Distributions: CLEARED vs NOT CLEARED",
        height=550,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
    )
    
    save_path = CHARTS_DIR / "return_distributions.html"
    fig.write_html(str(save_path))
    print(f"  💾 Chart 3 saved → charts/return_distributions.html")
    return fig


# ── Chart 4: Event Timeline (Scatter: each event on timeline) ──

def build_event_timeline():
    """Scatter plot showing each event's gap %, color-coded by bucket."""
    
    fig = go.Figure()
    
    if len(cleared_df) > 0:
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(cleared_df['earnings_date']),
            y=cleared_df['gap_pct'],
            mode='markers+text',
            name='CLEARED',
            marker=dict(color='#26a69a', size=14, symbol='triangle-up',
                        line=dict(width=1, color='white')),
            text=[f"${s:.0f}" for s in cleared_df['strike']],
            textposition='top center',
            textfont=dict(size=9),
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Gap: %{y:+.1f}%<br>"
                "Pre-Close: $%{customdata[0]:.2f}<br>"
                "Strike: $%{customdata[1]:.0f}<br>"
                "Next Close: $%{customdata[2]:.2f}<br>"
                "<extra>CLEARED</extra>"
            ),
            customdata=cleared_df[['pre_close', 'strike', 'next_close']].values,
        ))
    
    if len(not_cleared_df) > 0:
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(not_cleared_df['earnings_date']),
            y=not_cleared_df['gap_pct'],
            mode='markers+text',
            name='NOT CLEARED',
            marker=dict(color='#ef5350', size=14, symbol='triangle-down',
                        line=dict(width=1, color='white')),
            text=[f"${s:.0f}" for s in not_cleared_df['strike']],
            textposition='bottom center',
            textfont=dict(size=9),
            hovertemplate=(
                "Date: %{x|%Y-%m-%d}<br>"
                "Gap: %{y:+.1f}%<br>"
                "Pre-Close: $%{customdata[0]:.2f}<br>"
                "Strike: $%{customdata[1]:.0f}<br>"
                "Next Close: $%{customdata[2]:.2f}<br>"
                "<extra>NOT CLEARED</extra>"
            ),
            customdata=not_cleared_df[['pre_close', 'strike', 'next_close']].values,
        ))
    
    fig.add_hline(y=0, line_dash="dot", line_color="white", line_width=0.5)
    
    fig.update_layout(
        template="plotly_dark",
        title="NVDA Earnings Events: Gap % Timeline with Call Wall Outcome",
        xaxis_title="Earnings Date",
        yaxis_title="Overnight Gap (%)",
        height=500,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(0,0,0,0.5)'),
    )
    
    save_path = CHARTS_DIR / "event_timeline.html"
    fig.write_html(str(save_path))
    print(f"  💾 Chart 4 saved → charts/event_timeline.html")
    return fig


# Build all charts
build_forward_returns_chart()
build_winrate_chart()
build_distribution_chart()
build_event_timeline()
print()


# ═══════════════════════════════════════════════════════
# PHASE 6: SAVE OUTPUTS
# ═══════════════════════════════════════════════════════

print("PHASE 6: Saving outputs...")
print("-" * 50)

# Save full events table
events_df.to_csv(OUTPUT_DIR / "nvda_earnings_events.csv", index=False)
print(f"  💾 Events table → outputs/nvda_earnings_events.csv")

# Save bucket stats
stats_rows = [cleared_stats, not_cleared_stats]
stats_df = pd.DataFrame(stats_rows)
stats_df.to_csv(OUTPUT_DIR / "bucket_statistics.csv", index=False)
print(f"  💾 Bucket stats  → outputs/bucket_statistics.csv")

# Save summary text
summary_lines = [
    "=" * 70,
    "  NVDA POST-EARNINGS OPTIONS WALL STUDY — SUMMARY",
    "=" * 70,
    "",
    f"Study date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    f"Ticker: {TICKER}",
    f"Earnings events analyzed: {len(events_df)}",
    f"Clear threshold: next-day close > strike by >{CLEAR_THRESHOLD*100:.0f}%",
    "",
    "─" * 50,
    "QUESTION: Does clearing the key call wall predict whether the",
    "          post-earnings gap HOLDS or FADES?",
    "─" * 50,
    "",
    f"🟢 CLEARED events:      {cleared_stats['count']}",
    f"   Avg Gap:             {cleared_stats['avg_gap_pct']:+.2f}%",
    f"   Avg Next-Day O→C:    {cleared_stats['avg_next_day_oc']:+.2f}%",
    f"   Avg 3-Day Forward:   {cleared_stats['avg_fwd_3d']:+.2f}%",
    f"   Win Rate (1d):       {cleared_stats['win_rate_1d']:.0f}%",
    f"   Win Rate (3d):       {cleared_stats['win_rate_3d']:.0f}%",
    "",
    f"🔴 NOT CLEARED events:  {not_cleared_stats['count']}",
    f"   Avg Gap:             {not_cleared_stats['avg_gap_pct']:+.2f}%",
    f"   Avg Next-Day O→C:    {not_cleared_stats['avg_next_day_oc']:+.2f}%",
    f"   Avg 3-Day Forward:   {not_cleared_stats['avg_fwd_3d']:+.2f}%",
    f"   Win Rate (1d):       {not_cleared_stats['win_rate_1d']:.0f}%",
    f"   Win Rate (3d):       {not_cleared_stats['win_rate_3d']:.0f}%",
    "",
    "─" * 50,
    "INTERPRETATION:",
]

# Add interpretation
diff_1d = cleared_stats['avg_next_day_oc'] - not_cleared_stats['avg_next_day_oc']
diff_3d = cleared_stats['avg_fwd_3d'] - not_cleared_stats['avg_fwd_3d']
wr_diff_1d = cleared_stats['win_rate_1d'] - not_cleared_stats['win_rate_1d']

if not np.isnan(diff_1d):
    if abs(diff_1d) > 1.0:
        summary_lines.append(
            f"  ✅ Meaningful divergence in next-day returns: {diff_1d:+.2f}pp advantage for "
            f"{'CLEARED' if diff_1d > 0 else 'NOT CLEARED'} bucket."
        )
    else:
        summary_lines.append(
            f"  ⚪ Modest divergence in next-day returns ({diff_1d:+.2f}pp). Signal may be weak."
        )

if not np.isnan(diff_3d):
    if abs(diff_3d) > 1.5:
        summary_lines.append(
            f"  ✅ Notable 3-day return divergence: {diff_3d:+.2f}pp advantage for "
            f"{'CLEARED' if diff_3d > 0 else 'NOT CLEARED'} bucket."
        )
    else:
        summary_lines.append(
            f"  ⚪ Modest 3-day divergence ({diff_3d:+.2f}pp)."
        )

if not np.isnan(wr_diff_1d):
    if abs(wr_diff_1d) > 20:
        summary_lines.append(
            f"  ✅ Significant win rate gap: {wr_diff_1d:+.0f}pp in 1-day win rate."
        )
    else:
        summary_lines.append(
            f"  ⚪ Win rate difference: {wr_diff_1d:+.0f}pp (1-day)."
        )

summary_lines.extend([
    "",
    "─" * 50,
    "FULL EVENT TABLE:",
    "─" * 50,
    "",
    f"{'Date':<12} {'Pre-Close':>10} {'Strike':>8} {'Gap%':>7} {'NxtClose':>10} "
    f"{'Cleared':>10} {'O→C%':>7} {'3d Fwd%':>8}",
    "-" * 80,
])

for _, row in events_df.iterrows():
    bucket_flag = "CLEARED" if row['cleared'] else "NOT CLEARED"
    fwd3 = f"{row['fwd_3d_return_pct']:>+7.2f}%" if not pd.isna(row['fwd_3d_return_pct']) else "    N/A"
    summary_lines.append(
        f"{row['earnings_date']:<12} ${row['pre_close']:>8.2f} ${row['strike']:>6.0f} "
        f"{row['gap_pct']:>+6.1f}% ${row['next_close']:>8.2f} "
        f"{bucket_flag:>10} {row['next_day_return_oc_pct']:>+6.2f}% {fwd3}"
    )

summary_lines.extend([
    "",
    "=" * 70,
    "  Charts saved to: outputs/charts/",
    "  Data saved to:   outputs/nvda_earnings_events.csv",
    "=" * 70,
])

summary_text = "\n".join(summary_lines)
(OUTPUT_DIR / "study_summary.txt").write_text(summary_text, encoding='utf-8')
print(f"  💾 Summary text  → outputs/study_summary.txt")
print()


# ═══════════════════════════════════════════════════════
# FINAL OUTPUT
# ═══════════════════════════════════════════════════════

print()
print(summary_text)
print()
print("✅ Study complete!")

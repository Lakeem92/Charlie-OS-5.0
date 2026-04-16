"""
BABA China NBS November Data Release Event Study
Event-window price/volatility behavior around China NBS November macro data releases

Study: Event Window Analysis (NEW canonical study type)
Ticker: BABA (NYSE)
Data Source: Alpaca ONLY
Timezone: Central Time (CT)
Sessions: Premarket 3:00-8:29 CT + RTH 8:30-15:00 CT
Constraints: NO indicators (except ATR as volatility metric)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from shared.config.api_clients import AlpacaClient
import time

# Configuration
TICKER = "BABA"
EVENT_DATES = [
    "2020-12-15",
    "2021-12-15", 
    "2022-12-15",
    "2023-12-15",
    "2024-12-18"
]

DAILY_WINDOW_DAYS = 10  # [-10, +10] trading days
INTRADAY_DAYS = [0, 1]  # t and t+1
FORWARD_HORIZONS = [1, 2, 3, 5, 10]  # Trading days
INTRADAY_TIMEFRAME = '5Min'  # Try 5-min first
FALLBACK_TIMEFRAME = '15Min'  # Fallback if 5-min unavailable

# Timezone
CT = ZoneInfo("America/Chicago")
ET = ZoneInfo("America/New_York")

# Session times (CT)
PREMARKET_START = "03:00"
PREMARKET_END = "08:29"
RTH_START = "08:30"
RTH_END = "15:00"

# Output paths
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize client
client = AlpacaClient(paper_trading=True)

print("="*80)
print("BABA China NBS November Data Release Event Study")
print("="*80)
print(f"Ticker: {TICKER}")
print(f"Event Dates: {EVENT_DATES}")
print(f"Data Source: Alpaca")
print(f"Timezone: Central Time (CT)")
print(f"Sessions: Premarket (3:00-8:29 CT) + RTH (8:30-15:00 CT)")
print("="*80)

def fetch_daily_bars(symbol, start_date, end_date, max_retries=3):
    """Fetch daily bars with retry logic"""
    for attempt in range(max_retries):
        try:
            response = client.get_bars(
                symbol=symbol,
                timeframe='1Day',
                start=start_date,
                end=end_date,
                limit=10000,
                feed='iex'
            )
            
            if 'bars' in response and response['bars']:
                df = pd.DataFrame(response['bars'])
                df['timestamp'] = pd.to_datetime(df['t'])
                df['date'] = df['timestamp'].dt.date
                df = df.rename(columns={
                    'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'
                })
                return df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
            return pd.DataFrame()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt+1}/{max_retries} after error: {e}")
                time.sleep(2)
            else:
                print(f"  Failed to fetch daily bars: {e}")
                return pd.DataFrame()
    return pd.DataFrame()

def fetch_intraday_bars(symbol, date, timeframe='5Min', max_retries=3):
    """Fetch intraday bars for a specific date with retry logic"""
    # Expand the window to ensure we get premarket data
    start = pd.Timestamp(date).tz_localize('America/New_York').replace(hour=3, minute=0) - timedelta(hours=5)
    end = pd.Timestamp(date).tz_localize('America/New_York').replace(hour=16, minute=0)
    
    for attempt in range(max_retries):
        try:
            response = client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start.isoformat(),
                end=end.isoformat(),
                limit=10000,
                feed='iex'
            )
            
            if 'bars' in response and response['bars']:
                df = pd.DataFrame(response['bars'])
                df['timestamp'] = pd.to_datetime(df['t']).dt.tz_convert(CT)
                df = df.rename(columns={
                    'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'
                })
                # Filter to just the target date in CT
                target_date = pd.Timestamp(date).date()
                df['date'] = df['timestamp'].dt.date
                df = df[df['date'] == target_date].copy()
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            return pd.DataFrame()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt+1}/{max_retries} for intraday on {date}: {e}")
                time.sleep(2)
            else:
                print(f"  Failed to fetch intraday bars for {date}: {e}")
                return pd.DataFrame()
    return pd.DataFrame()

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    df = df.copy()
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df

def get_trading_days_around_event(all_daily_df, event_date, window_days):
    """Get trading days in window around event date"""
    event_date = pd.Timestamp(event_date).date()
    all_dates = sorted(all_daily_df['date'].unique())
    
    # Find event date or next trading day
    if event_date in all_dates:
        event_idx = all_dates.index(event_date)
    else:
        # Find next trading day
        later_dates = [d for d in all_dates if d > event_date]
        if not later_dates:
            return None, None
        event_date = later_dates[0]
        event_idx = all_dates.index(event_date)
    
    # Get window
    start_idx = max(0, event_idx - window_days)
    end_idx = min(len(all_dates) - 1, event_idx + window_days)
    
    window_dates = all_dates[start_idx:end_idx+1]
    return event_date, window_dates

def compute_daily_metrics(daily_df, event_date, window_dates):
    """Compute daily-level metrics for event window"""
    results = []
    daily_df = calculate_atr(daily_df)
    
    event_date = pd.Timestamp(event_date).date()
    event_idx = window_dates.index(event_date)
    
    for i, date in enumerate(window_dates):
        rel_day = i - event_idx
        row = daily_df[daily_df['date'] == date]
        
        if row.empty:
            continue
            
        row = row.iloc[0]
        
        # Get prior close
        prior_close = None
        if i > 0:
            prior_date = window_dates[i-1]
            prior_row = daily_df[daily_df['date'] == prior_date]
            if not prior_row.empty:
                prior_close = prior_row.iloc[0]['close']
        
        # Calculate metrics
        metrics = {
            'event_date': str(event_date),
            'date': str(date),
            'rel_day': rel_day,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        }
        
        # Returns and ranges
        if prior_close is not None:
            metrics['close_to_close_return_pct'] = ((row['close'] - prior_close) / prior_close) * 100
            metrics['gap_pct'] = ((row['open'] - prior_close) / prior_close) * 100
        else:
            metrics['close_to_close_return_pct'] = np.nan
            metrics['gap_pct'] = np.nan
        
        metrics['intraday_return_pct'] = ((row['close'] - row['open']) / row['open']) * 100
        metrics['daily_range_pct'] = ((row['high'] - row['low']) / row['open']) * 100
        metrics['true_range'] = row.get('tr', np.nan)
        metrics['atr_14'] = row.get('atr', np.nan)
        
        results.append(metrics)
    
    return pd.DataFrame(results)

def compute_forward_metrics(daily_df, event_date, window_dates, horizons):
    """Compute forward returns and risk metrics"""
    event_date = pd.Timestamp(event_date).date()
    event_row = daily_df[daily_df['date'] == event_date]
    
    if event_row.empty:
        return None
    
    event_row = event_row.iloc[0]
    event_close = event_row['close']
    event_idx = list(window_dates).index(event_date)
    
    # Get prior close for gap calculation
    prior_close = None
    if event_idx > 0:
        prior_date = window_dates[event_idx - 1]
        prior_row = daily_df[daily_df['date'] == prior_date]
        if not prior_row.empty:
            prior_close = prior_row.iloc[0]['close']
    
    metrics = {
        'event_date': str(event_date),
        'event_close': event_close,
    }
    
    # Gap and intraday
    if prior_close is not None:
        metrics['gap_pct'] = ((event_row['open'] - prior_close) / prior_close) * 100
    else:
        metrics['gap_pct'] = np.nan
    
    metrics['intraday_pct'] = ((event_row['close'] - event_row['open']) / event_row['open']) * 100
    
    # Forward returns
    for h in horizons:
        future_idx = event_idx + h
        if future_idx < len(window_dates):
            future_date = window_dates[future_idx]
            future_row = daily_df[daily_df['date'] == future_date]
            if not future_row.empty:
                future_close = future_row.iloc[0]['close']
                metrics[f'fwd_{h}d_return_pct'] = ((future_close - event_close) / event_close) * 100
            else:
                metrics[f'fwd_{h}d_return_pct'] = np.nan
        else:
            metrics[f'fwd_{h}d_return_pct'] = np.nan
    
    # MAE, MFE, Max DD over +10 days
    future_dates = window_dates[event_idx+1:min(event_idx+11, len(window_dates))]
    future_data = daily_df[daily_df['date'].isin(future_dates)]
    
    if not future_data.empty:
        highs = future_data['high'].values
        lows = future_data['low'].values
        closes = future_data['close'].values
        
        mfe = ((highs.max() - event_close) / event_close) * 100
        mae = ((lows.min() - event_close) / event_close) * 100
        
        # Max drawdown from event close
        max_dd = 0
        for c in closes:
            dd = ((c - event_close) / event_close) * 100
            if dd < max_dd:
                max_dd = dd
        
        metrics['mfe_pct'] = mfe
        metrics['mae_pct'] = mae
        metrics['max_dd_pct'] = max_dd
    else:
        metrics['mfe_pct'] = np.nan
        metrics['mae_pct'] = np.nan
        metrics['max_dd_pct'] = np.nan
    
    return metrics

def compute_intraday_metrics(intraday_df, date):
    """Compute intraday session metrics"""
    if intraday_df.empty:
        return None
    
    # Parse session times
    premarket_start = pd.Timestamp(f"{date} {PREMARKET_START}:00").tz_localize(CT)
    premarket_end = pd.Timestamp(f"{date} {PREMARKET_END}:59").tz_localize(CT)
    rth_start = pd.Timestamp(f"{date} {RTH_START}:00").tz_localize(CT)
    rth_end = pd.Timestamp(f"{date} {RTH_END}:00").tz_localize(CT)
    
    # Filter sessions
    premarket = intraday_df[(intraday_df['timestamp'] >= premarket_start) & 
                            (intraday_df['timestamp'] <= premarket_end)]
    rth = intraday_df[(intraday_df['timestamp'] >= rth_start) & 
                      (intraday_df['timestamp'] <= rth_end)]
    full_session = intraday_df[(intraday_df['timestamp'] >= premarket_start) & 
                               (intraday_df['timestamp'] <= rth_end)]
    
    metrics = {
        'date': str(date),
        'premarket_bars': len(premarket),
        'rth_bars': len(rth),
        'full_session_bars': len(full_session)
    }
    
    # Premarket metrics
    if not premarket.empty:
        pm_first = premarket.iloc[0]['close']
        pm_last = premarket.iloc[-1]['close']
        metrics['premarket_return_pct'] = ((pm_last - pm_first) / pm_first) * 100
    else:
        metrics['premarket_return_pct'] = np.nan
    
    # RTH metrics
    if not rth.empty:
        rth_first = rth.iloc[0]['close']
        rth_last = rth.iloc[-1]['close']
        metrics['rth_return_pct'] = ((rth_last - rth_first) / rth_first) * 100
    else:
        metrics['rth_return_pct'] = np.nan
    
    # Full session metrics
    if not full_session.empty:
        session_open = full_session.iloc[0]['open']
        session_high = full_session['high'].max()
        session_low = full_session['low'].min()
        
        metrics['full_session_range_pct'] = ((session_high - session_low) / session_open) * 100
        
        # Time of extremes
        high_row = full_session[full_session['high'] == session_high].iloc[0]
        low_row = full_session[full_session['low'] == session_low].iloc[0]
        metrics['session_high_time_ct'] = high_row['timestamp'].strftime('%H:%M:%S')
        metrics['session_low_time_ct'] = low_row['timestamp'].strftime('%H:%M:%S')
        
        # Largest 5-min move
        full_session = full_session.copy()
        full_session['bar_return_pct'] = ((full_session['close'] - full_session['open']) / full_session['open']) * 100
        full_session['abs_bar_return'] = full_session['bar_return_pct'].abs()
        largest_move_row = full_session.loc[full_session['abs_bar_return'].idxmax()]
        metrics['largest_5min_move_pct'] = largest_move_row['bar_return_pct']
        metrics['largest_5min_move_time_ct'] = largest_move_row['timestamp'].strftime('%H:%M:%S')
        
        # Realized volatility (annualized)
        # Using log returns
        full_session_sorted = full_session.sort_values('timestamp')
        log_returns = np.log(full_session_sorted['close'] / full_session_sorted['close'].shift(1)).dropna()
        
        if len(log_returns) > 1:
            # Annualization: 252 trading days, assuming 5-min bars
            # Number of 5-min periods in a trading day (6.5 hours * 60 / 5 = 78 periods)
            periods_per_day = 78
            realized_vol = log_returns.std() * np.sqrt(periods_per_day * 252) * 100
            metrics['full_session_realized_vol_annualized'] = realized_vol
        else:
            metrics['full_session_realized_vol_annualized'] = np.nan
        
        # Separate realized vol for premarket and RTH
        if not premarket.empty and len(premarket) > 1:
            pm_sorted = premarket.sort_values('timestamp')
            pm_log_returns = np.log(pm_sorted['close'] / pm_sorted['close'].shift(1)).dropna()
            if len(pm_log_returns) > 1:
                pm_vol = pm_log_returns.std() * np.sqrt(periods_per_day * 252) * 100
                metrics['premarket_realized_vol_annualized'] = pm_vol
            else:
                metrics['premarket_realized_vol_annualized'] = np.nan
        else:
            metrics['premarket_realized_vol_annualized'] = np.nan
        
        if not rth.empty and len(rth) > 1:
            rth_sorted = rth.sort_values('timestamp')
            rth_log_returns = np.log(rth_sorted['close'] / rth_sorted['close'].shift(1)).dropna()
            if len(rth_log_returns) > 1:
                rth_vol = rth_log_returns.std() * np.sqrt(periods_per_day * 252) * 100
                metrics['rth_realized_vol_annualized'] = rth_vol
            else:
                metrics['rth_realized_vol_annualized'] = np.nan
        else:
            metrics['rth_realized_vol_annualized'] = np.nan
    else:
        metrics['full_session_range_pct'] = np.nan
        metrics['session_high_time_ct'] = None
        metrics['session_low_time_ct'] = None
        metrics['largest_5min_move_pct'] = np.nan
        metrics['largest_5min_move_time_ct'] = None
        metrics['full_session_realized_vol_annualized'] = np.nan
        metrics['premarket_realized_vol_annualized'] = np.nan
        metrics['rth_realized_vol_annualized'] = np.nan
    
    return metrics

# ============================================================================
# MAIN EXECUTION
# ============================================================================

print("\n[1/6] Fetching daily data...")

# Determine full date range needed
all_dates = [pd.Timestamp(d) for d in EVENT_DATES]
earliest = min(all_dates) - timedelta(days=30)  # Buffer for window
latest = max(all_dates) + timedelta(days=30)

daily_df = fetch_daily_bars(TICKER, earliest.strftime('%Y-%m-%d'), latest.strftime('%Y-%m-%d'))

if daily_df.empty:
    print("ERROR: Could not fetch daily data from Alpaca")
    sys.exit(1)

print(f"  Fetched {len(daily_df)} daily bars")

# ============================================================================
print("\n[2/6] Computing daily window metrics...")

all_daily_window_results = []

for event_date_str in EVENT_DATES:
    print(f"  Processing event: {event_date_str}")
    
    event_date, window_dates = get_trading_days_around_event(daily_df, event_date_str, DAILY_WINDOW_DAYS)
    
    if event_date is None:
        print(f"    WARNING: Could not find trading days around {event_date_str}")
        continue
    
    if str(event_date) != event_date_str:
        print(f"    NOTE: {event_date_str} was not a trading day; using {event_date} instead")
    
    daily_metrics = compute_daily_metrics(daily_df, event_date, window_dates)
    all_daily_window_results.append(daily_metrics)

daily_window_df = pd.concat(all_daily_window_results, ignore_index=True)
daily_window_csv = OUTPUT_DIR / "baba_nbs_event_window_daily.csv"
daily_window_df.to_csv(daily_window_csv, index=False)
print(f"  Saved: {daily_window_csv}")

# ============================================================================
print("\n[3/6] Computing forward returns...")

forward_results = []

for event_date_str in EVENT_DATES:
    event_date, window_dates = get_trading_days_around_event(daily_df, event_date_str, DAILY_WINDOW_DAYS)
    
    if event_date is None:
        continue
    
    forward_metrics = compute_forward_metrics(daily_df, event_date, window_dates, FORWARD_HORIZONS)
    if forward_metrics:
        forward_results.append(forward_metrics)

forward_df = pd.DataFrame(forward_results)
forward_csv = OUTPUT_DIR / "baba_nbs_forward_returns.csv"
forward_df.to_csv(forward_csv, index=False)
print(f"  Saved: {forward_csv}")

# ============================================================================
print("\n[4/6] Fetching intraday data and computing intraday metrics...")

intraday_results = []
used_timeframe = INTRADAY_TIMEFRAME

# Test if 5-min data is available
test_date = EVENT_DATES[-1]  # Most recent event
test_df = fetch_intraday_bars(TICKER, test_date, INTRADAY_TIMEFRAME)

if test_df.empty or len(test_df) < 10:
    print(f"  WARNING: {INTRADAY_TIMEFRAME} bars insufficient or unavailable")
    print(f"  Falling back to {FALLBACK_TIMEFRAME}")
    used_timeframe = FALLBACK_TIMEFRAME

for event_date_str in EVENT_DATES:
    event_date, window_dates = get_trading_days_around_event(daily_df, event_date_str, DAILY_WINDOW_DAYS)
    
    if event_date is None:
        continue
    
    event_idx = list(window_dates).index(event_date)
    
    # Fetch t and t+1
    for rel_day in INTRADAY_DAYS:
        target_idx = event_idx + rel_day
        if target_idx < len(window_dates):
            target_date = window_dates[target_idx]
            print(f"  Fetching intraday for {target_date} (event {event_date}, t+{rel_day})...")
            
            intraday_df = fetch_intraday_bars(TICKER, target_date, used_timeframe)
            
            if not intraday_df.empty:
                metrics = compute_intraday_metrics(intraday_df, target_date)
                if metrics:
                    metrics['event_date'] = str(event_date)
                    metrics['rel_day'] = rel_day
                    intraday_results.append(metrics)
            else:
                print(f"    No intraday data for {target_date}")

intraday_metrics_df = pd.DataFrame(intraday_results)
intraday_csv = OUTPUT_DIR / "baba_nbs_intraday_metrics.csv"
intraday_metrics_df.to_csv(intraday_csv, index=False)
print(f"  Saved: {intraday_csv}")
print(f"  Timeframe used: {used_timeframe}")

# ============================================================================
print("\n[5/6] Generating charts...")

# Chart 1: Mean return by relative day
plt.figure(figsize=(12, 6))
grouped = daily_window_df.groupby('rel_day')['close_to_close_return_pct'].agg(['mean', 'std', 'count'])
grouped = grouped.sort_index()

plt.plot(grouped.index, grouped['mean'], marker='o', linewidth=2, markersize=6)
plt.axhline(0, color='black', linestyle='--', linewidth=0.8)
plt.axvline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Event Day')
plt.xlabel('Relative Day (0 = Event Date)')
plt.ylabel('Mean Close-to-Close Return (%)')
plt.title(f'{TICKER} Mean Daily Return by Relative Day\nChina NBS November Data Releases')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
chart1_path = OUTPUT_DIR / "baba_nbs_rel_day_mean_return.png"
plt.savefig(chart1_path, dpi=150)
plt.close()
print(f"  Saved: {chart1_path}")

# Chart 2: Mean range by relative day
plt.figure(figsize=(12, 6))
grouped_range = daily_window_df.groupby('rel_day')['daily_range_pct'].agg(['mean', 'std', 'count'])
grouped_range = grouped_range.sort_index()

plt.plot(grouped_range.index, grouped_range['mean'], marker='o', linewidth=2, markersize=6, color='orange')
plt.axvline(0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Event Day')
plt.xlabel('Relative Day (0 = Event Date)')
plt.ylabel('Mean Daily Range (%)')
plt.title(f'{TICKER} Mean Daily Range by Relative Day\nChina NBS November Data Releases')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
chart2_path = OUTPUT_DIR / "baba_nbs_rel_day_mean_range.png"
plt.savefig(chart2_path, dpi=150)
plt.close()
print(f"  Saved: {chart2_path}")

# Chart 3: Forward return distributions
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()

forward_horizons_to_plot = [1, 2, 3, 5]

for i, h in enumerate(forward_horizons_to_plot):
    col = f'fwd_{h}d_return_pct'
    if col in forward_df.columns:
        data = forward_df[col].dropna()
        if len(data) > 0:
            axes[i].hist(data, bins=10, alpha=0.7, edgecolor='black')
            axes[i].axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {data.mean():.2f}%')
            axes[i].axvline(0, color='black', linestyle='-', linewidth=0.8)
            axes[i].set_xlabel('Return (%)')
            axes[i].set_ylabel('Frequency')
            axes[i].set_title(f'+{h}d Forward Returns (n={len(data)})')
            axes[i].legend()
            axes[i].grid(True, alpha=0.3)

plt.tight_layout()
chart3_path = OUTPUT_DIR / "baba_nbs_forward_return_distributions.png"
plt.savefig(chart3_path, dpi=150)
plt.close()
print(f"  Saved: {chart3_path}")

# ============================================================================
print("\n[6/6] Generating markdown report...")

report_md = f"""# BABA China NBS November Data Release Study Report

**Study Type:** Event Window Analysis (NEW canonical study type)  
**Execution Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Ticker:** {TICKER} (NYSE)  
**Event:** China NBS November macro data releases  

---

## Data Source & Configuration

- **Data Source:** Alpaca (IEX feed)
- **Timezone:** Central Time (CT)
- **Sessions:**
  - Premarket: 3:00-8:29 AM CT
  - RTH: 8:30 AM-3:00 PM CT
- **Event Dates:**
"""

for ed in EVENT_DATES:
    report_md += f"  - {ed}\n"

report_md += f"""
- **Daily Window:** [-10, +10] trading days
- **Intraday Analysis:** Event day (t) and next day (t+1)
- **Intraday Timeframe:** {used_timeframe}
- **Forward Return Horizons:** +1, +2, +3, +5, +10 trading days

---

## Sample Size & Limitations

- **Number of Events:** {len(EVENT_DATES)}
- **Total Daily Observations:** {len(daily_window_df)}
- **Intraday Sessions Analyzed:** {len(intraday_metrics_df)}

**Limitations:**
- Small sample size (n={len(EVENT_DATES)}) limits statistical power
- Results are descriptive, not predictive
- China macro data releases may have varying market impact year-to-year
- No control for concurrent market events or regime changes
- Alpaca IEX feed may have limited premarket coverage for earlier years

---

## Key Findings

### A. Forward Returns from Event Close

"""

# Calculate summary stats for forward returns
for h in FORWARD_HORIZONS:
    col = f'fwd_{h}d_return_pct'
    if col in forward_df.columns:
        data = forward_df[col].dropna()
        if len(data) > 0:
            mean_ret = data.mean()
            median_ret = data.median()
            pos_count = (data > 0).sum()
            hit_rate = (pos_count / len(data)) * 100
            report_md += f"**+{h} Day:**\n"
            report_md += f"- Mean: {mean_ret:.2f}%\n"
            report_md += f"- Median: {median_ret:.2f}%\n"
            report_md += f"- Hit Rate (% positive): {hit_rate:.1f}% ({pos_count}/{len(data)})\n"
            report_md += f"- Range: [{data.min():.2f}%, {data.max():.2f}%]\n\n"

report_md += """
### B. Event Day Behavior

"""

# Event day stats
event_day_data = daily_window_df[daily_window_df['rel_day'] == 0]
if not event_day_data.empty:
    gap_mean = event_day_data['gap_pct'].mean()
    intraday_mean = event_day_data['intraday_return_pct'].mean()
    range_mean = event_day_data['daily_range_pct'].mean()
    
    report_md += f"- **Mean Gap:** {gap_mean:.2f}%\n"
    report_md += f"- **Mean Intraday Return:** {intraday_mean:.2f}%\n"
    report_md += f"- **Mean Daily Range:** {range_mean:.2f}%\n\n"

# Max drawdown and MAE/MFE
if not forward_df.empty:
    mae_mean = forward_df['mae_pct'].mean()
    mfe_mean = forward_df['mfe_pct'].mean()
    max_dd_mean = forward_df['max_dd_pct'].mean()
    
    report_md += f"""
### C. Risk Metrics (10-day post-event window)

- **Mean Max Favorable Excursion (MFE):** {mfe_mean:.2f}%
- **Mean Max Adverse Excursion (MAE):** {mae_mean:.2f}%
- **Mean Max Drawdown:** {max_dd_mean:.2f}%

"""

report_md += """
### D. Volatility Analysis

"""

# Compare event day range to mean pre-event range
pre_event_data = daily_window_df[daily_window_df['rel_day'] < 0]
if not pre_event_data.empty and not event_day_data.empty:
    pre_range_mean = pre_event_data['daily_range_pct'].mean()
    event_range_mean = event_day_data['daily_range_pct'].mean()
    range_expansion = ((event_range_mean - pre_range_mean) / pre_range_mean) * 100
    
    report_md += f"**Daily Range Comparison:**\n"
    report_md += f"- Mean Pre-Event Range (days -10 to -1): {pre_range_mean:.2f}%\n"
    report_md += f"- Mean Event Day Range (day 0): {event_range_mean:.2f}%\n"
    report_md += f"- **Range Expansion:** {range_expansion:+.1f}%\n\n"

# ATR comparison
event_atr = event_day_data['atr_14'].mean()
pre_atr = pre_event_data['atr_14'].mean()
if not np.isnan(event_atr) and not np.isnan(pre_atr):
    atr_expansion = ((event_atr - pre_atr) / pre_atr) * 100
    report_md += f"**ATR(14) Comparison:**\n"
    report_md += f"- Mean Pre-Event ATR: ${pre_atr:.2f}\n"
    report_md += f"- Mean Event Day ATR: ${event_atr:.2f}\n"
    report_md += f"- **ATR Expansion:** {atr_expansion:+.1f}%\n\n"

# Intraday volatility
if not intraday_metrics_df.empty:
    event_intraday = intraday_metrics_df[intraday_metrics_df['rel_day'] == 0]
    if not event_intraday.empty:
        full_vol = event_intraday['full_session_realized_vol_annualized'].mean()
        pm_vol = event_intraday['premarket_realized_vol_annualized'].mean()
        rth_vol = event_intraday['rth_realized_vol_annualized'].mean()
        
        report_md += f"**Intraday Realized Volatility (Event Day, Annualized):**\n"
        if not np.isnan(pm_vol):
            report_md += f"- Premarket: {pm_vol:.1f}%\n"
        if not np.isnan(rth_vol):
            report_md += f"- RTH: {rth_vol:.1f}%\n"
        if not np.isnan(full_vol):
            report_md += f"- Full Session: {full_vol:.1f}%\n\n"

report_md += """
---

## Interpretation

This study provides a descriptive analysis of BABA's price and volatility behavior around China NBS November macro data releases. Key observations:

1. **Small Sample Limitation:** With only 5 events, individual outliers can heavily influence means and percentages.
2. **Volatility Context:** Compare daily range and ATR expansion to assess whether these releases systematically increase volatility.
3. **Forward Return Asymmetry:** Examine hit rates and mean returns to identify any directional bias following the event.
4. **Intraday Timing:** Session high/low timing and premarket vs RTH behavior can inform intraday positioning.

**No indicators were used** (except ATR as a volatility metric per constraints). All analysis is based on raw price/volatility metrics.

---

## Outputs

All outputs are saved in the `outputs/` directory:

1. `baba_nbs_event_window_daily.csv` — Daily OHLCV and metrics for each event window
2. `baba_nbs_forward_returns.csv` — Forward returns and risk metrics for each event
3. `baba_nbs_intraday_metrics.csv` — Intraday session metrics (premarket + RTH)
4. `baba_nbs_rel_day_mean_return.png` — Mean return by relative day chart
5. `baba_nbs_rel_day_mean_range.png` — Mean daily range by relative day chart
6. `baba_nbs_forward_return_distributions.png` — Forward return distributions
7. `baba_nbs_study1_report.md` — This report

---

**Study Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

report_path = OUTPUT_DIR / "baba_nbs_study1_report.md"
with open(report_path, 'w') as f:
    f.write(report_md)

print(f"  Saved: {report_path}")

# ============================================================================
print("\n" + "="*80)
print("EXECUTION COMPLETE")
print("="*80)
print("\nConsole Summary:")
print(f"  Ticker: {TICKER}")
print(f"  Events Analyzed: {len(EVENT_DATES)}")
print(f"  Daily Observations: {len(daily_window_df)}")
print(f"  Intraday Sessions: {len(intraday_metrics_df)}")
print(f"  Timeframe Used: {used_timeframe}")
print()

# Summary stats
if not forward_df.empty:
    print("Forward Returns Summary:")
    for h in [1, 2, 3, 5, 10]:
        col = f'fwd_{h}d_return_pct'
        if col in forward_df.columns:
            data = forward_df[col].dropna()
            if len(data) > 0:
                print(f"  +{h}d: Mean={data.mean():.2f}%, Median={data.median():.2f}%, HitRate={((data>0).sum()/len(data)*100):.1f}%")

print()

if not event_day_data.empty:
    print("Event Day Behavior:")
    print(f"  Mean Gap: {event_day_data['gap_pct'].mean():.2f}%")
    print(f"  Mean Intraday: {event_day_data['intraday_return_pct'].mean():.2f}%")
    print(f"  Mean Range: {event_day_data['daily_range_pct'].mean():.2f}%")

print()
print("Volatility:")
if not pre_event_data.empty and not event_day_data.empty:
    pre_range = pre_event_data['daily_range_pct'].mean()
    event_range = event_day_data['daily_range_pct'].mean()
    print(f"  Pre-Event Range: {pre_range:.2f}%")
    print(f"  Event Day Range: {event_range:.2f}%")
    print(f"  Range Expansion: {((event_range - pre_range) / pre_range * 100):+.1f}%")

print()
print("Output Files:")
print(f"  {daily_window_csv}")
print(f"  {forward_csv}")
print(f"  {intraday_csv}")
print(f"  {chart1_path}")
print(f"  {chart2_path}")
print(f"  {chart3_path}")
print(f"  {report_path}")
print()
print("="*80)

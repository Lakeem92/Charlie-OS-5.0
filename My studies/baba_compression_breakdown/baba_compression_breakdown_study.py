"""
BABA Compression-Range Breakdown Study
Compression-range breakdown follow-through in BABA (daily + intraday confirmation)

Study: Compression-Range Breakdown Analysis (NEW canonical study type)
Ticker: BABA (NYSE)
Period: 2016-01-01 through 2025-12-13
Data Source: Alpaca ONLY
Timezone: Central Time (CT)
Sessions: Premarket 3:00-8:29 CT + RTH 8:30-15:00 CT
Constraints: NO indicators (only ATR as volatility metric)
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
from shared.config.api_clients import AlpacaClient
import time

# Configuration
TICKER = "BABA"
START_DATE = "2016-01-01"
END_DATE = "2025-12-13"

# Compression parameters (DO NOT MODIFY)
LOOKBACK_N = 20  # 20 trading days
COMPRESSION_PERCENTILE = 20  # Bottom 20th percentile
RANGE_EXPANSION_MULTIPLIER = 1.25  # 1.25x median for expansion flag

# Forward horizons
FORWARD_HORIZONS = [1, 2, 3, 5, 10, 20]

# Intraday parameters
INTRADAY_TIMEFRAME = '5Min'
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
print("BABA Compression-Range Breakdown Study")
print("="*80)
print(f"Ticker: {TICKER}")
print(f"Period: {START_DATE} to {END_DATE}")
print(f"Compression lookback: {LOOKBACK_N} days")
print(f"Compression threshold: Bottom {COMPRESSION_PERCENTILE}th percentile")
print(f"Data Source: Alpaca")
print(f"Timezone: Central Time (CT)")
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
                df = df.sort_values('date').reset_index(drop=True)
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
    """Fetch intraday bars for a specific date"""
    # Expand window for premarket
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
                target_date = pd.Timestamp(date).date()
                df['date'] = df['timestamp'].dt.date
                df = df[df['date'] == target_date].copy()
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            return pd.DataFrame()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
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

def compute_compression_ranges(daily_df, lookback):
    """Compute rolling 20-day compression ranges"""
    results = []
    
    for i in range(lookback, len(daily_df)):
        window = daily_df.iloc[i-lookback:i]  # 20 days BEFORE day i
        
        range_high = window['high'].max()
        range_low = window['low'].min()
        close_prev = daily_df.iloc[i-1]['close']
        
        compression_range_pct = ((range_high - range_low) / close_prev) * 100
        
        results.append({
            'index': i,
            'date': daily_df.iloc[i]['date'],
            'range_high': range_high,
            'range_low': range_low,
            'compression_range_pct': compression_range_pct
        })
    
    return pd.DataFrame(results)

def identify_breakdowns_and_baseline(daily_df, compression_df, compression_threshold):
    """Identify breakdown and baseline events"""
    breakdowns = []
    baseline = []
    
    for _, row in compression_df.iterrows():
        idx = row['index']
        date = row['date']
        range_low = row['range_low']
        compression_range_pct = row['compression_range_pct']
        
        # Check if compression qualified (bottom 20th percentile)
        if compression_range_pct <= compression_threshold:
            day_data = daily_df.iloc[idx]
            
            # Check breakdown condition
            if day_data['close'] < range_low:
                breakdowns.append({
                    'date': date,
                    'index': idx,
                    'range_high': row['range_high'],
                    'range_low': range_low,
                    'compression_range_pct': compression_range_pct,
                    'open': day_data['open'],
                    'high': day_data['high'],
                    'low': day_data['low'],
                    'close': day_data['close'],
                    'volume': day_data['volume']
                })
            else:
                # Baseline: compression qualified but no breakdown
                baseline.append({
                    'date': date,
                    'index': idx,
                    'range_high': row['range_high'],
                    'range_low': range_low,
                    'compression_range_pct': compression_range_pct,
                    'open': day_data['open'],
                    'high': day_data['high'],
                    'low': day_data['low'],
                    'close': day_data['close'],
                    'volume': day_data['volume']
                })
    
    return pd.DataFrame(breakdowns), pd.DataFrame(baseline)

def compute_forward_metrics(daily_df, event_idx, entry_close, horizons):
    """Compute forward returns, MAE, MFE, max drawdown"""
    metrics = {}
    
    for h in horizons:
        future_idx = event_idx + h
        
        if future_idx < len(daily_df):
            # Get data from event+1 to event+h
            future_data = daily_df.iloc[event_idx+1:future_idx+1]
            
            if not future_data.empty:
                # Forward return
                future_close = daily_df.iloc[future_idx]['close']
                fwd_return = ((future_close - entry_close) / entry_close) * 100
                metrics[f'fwd_{h}d_return_pct'] = fwd_return
                
                # MAE and MFE
                highs = future_data['high'].values
                lows = future_data['low'].values
                
                mfe = ((highs.max() - entry_close) / entry_close) * 100
                mae = ((lows.min() - entry_close) / entry_close) * 100
                
                metrics[f'mfe_{h}d_pct'] = mfe
                metrics[f'mae_{h}d_pct'] = mae
                
                # Max drawdown (close-to-close)
                closes = future_data['close'].values
                max_dd = 0
                for c in closes:
                    dd = ((c - entry_close) / entry_close) * 100
                    if dd < max_dd:
                        max_dd = dd
                
                metrics[f'max_dd_{h}d_pct'] = max_dd
            else:
                metrics[f'fwd_{h}d_return_pct'] = np.nan
                metrics[f'mfe_{h}d_pct'] = np.nan
                metrics[f'mae_{h}d_pct'] = np.nan
                metrics[f'max_dd_{h}d_pct'] = np.nan
        else:
            metrics[f'fwd_{h}d_return_pct'] = np.nan
            metrics[f'mfe_{h}d_pct'] = np.nan
            metrics[f'mae_{h}d_pct'] = np.nan
            metrics[f'max_dd_{h}d_pct'] = np.nan
    
    return metrics

def compute_range_expansion_metrics(daily_df, event_idx):
    """Compute range expansion metrics for breakdown day"""
    # Get prior 20 days
    prior_window = daily_df.iloc[event_idx-LOOKBACK_N:event_idx]
    event_day = daily_df.iloc[event_idx]
    
    # Daily range %
    event_range_pct = ((event_day['high'] - event_day['low']) / event_day['open']) * 100
    prior_ranges = ((prior_window['high'] - prior_window['low']) / prior_window['open']) * 100
    median_prior_range = prior_ranges.median()
    
    # True Range
    prior_tr = []
    for i in range(len(prior_window)):
        if i > 0:
            h_l = prior_window.iloc[i]['high'] - prior_window.iloc[i]['low']
            h_pc = abs(prior_window.iloc[i]['high'] - prior_window.iloc[i-1]['close'])
            l_pc = abs(prior_window.iloc[i]['low'] - prior_window.iloc[i-1]['close'])
            tr = max(h_l, h_pc, l_pc)
            prior_tr.append(tr)
    
    median_prior_tr = np.median(prior_tr) if prior_tr else np.nan
    
    # Event day TR
    if event_idx > 0:
        prev_close = daily_df.iloc[event_idx-1]['close']
        h_l = event_day['high'] - event_day['low']
        h_pc = abs(event_day['high'] - prev_close)
        l_pc = abs(event_day['low'] - prev_close)
        event_tr = max(h_l, h_pc, l_pc)
    else:
        event_tr = event_day['high'] - event_day['low']
    
    # Expansion flags
    range_expansion_flag = 1 if event_range_pct >= RANGE_EXPANSION_MULTIPLIER * median_prior_range else 0
    
    return {
        'event_range_pct': event_range_pct,
        'median_prior_range_pct': median_prior_range,
        'event_tr': event_tr,
        'median_prior_tr': median_prior_tr,
        'range_expansion_flag': range_expansion_flag
    }

def compute_intraday_breakdown_metrics(intraday_df, range_low, date):
    """Compute intraday breakdown metrics"""
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
    
    metrics = {
        'date': str(date),
        'range_low': range_low
    }
    
    # Premarket breakdown
    if not premarket.empty:
        pm_low = premarket['low'].min()
        metrics['premarket_broke_below'] = 1 if pm_low < range_low else 0
    else:
        metrics['premarket_broke_below'] = np.nan
    
    # RTH breakdown
    if not rth.empty:
        rth_low = rth['low'].min()
        rth_close = rth.iloc[-1]['close']
        metrics['rth_broke_below'] = 1 if rth_low < range_low else 0
        metrics['rth_close_vs_range_low_pct'] = ((rth_close - range_low) / range_low) * 100
    else:
        metrics['rth_broke_below'] = np.nan
        metrics['rth_close_vs_range_low_pct'] = np.nan
    
    # Largest 5-min move
    if not intraday_df.empty:
        intraday_df_copy = intraday_df.copy()
        intraday_df_copy['bar_return_pct'] = ((intraday_df_copy['close'] - intraday_df_copy['open']) / 
                                               intraday_df_copy['open']) * 100
        intraday_df_copy['abs_bar_return'] = intraday_df_copy['bar_return_pct'].abs()
        
        if not intraday_df_copy.empty and intraday_df_copy['abs_bar_return'].max() > 0:
            largest_move_row = intraday_df_copy.loc[intraday_df_copy['abs_bar_return'].idxmax()]
            metrics['largest_5min_move_pct'] = largest_move_row['bar_return_pct']
            metrics['largest_5min_move_time_ct'] = largest_move_row['timestamp'].strftime('%H:%M:%S')
        else:
            metrics['largest_5min_move_pct'] = np.nan
            metrics['largest_5min_move_time_ct'] = None
    else:
        metrics['largest_5min_move_pct'] = np.nan
        metrics['largest_5min_move_time_ct'] = None
    
    return metrics

# ============================================================================
# MAIN EXECUTION
# ============================================================================

print("\n[1/7] Fetching daily data...")
daily_df = fetch_daily_bars(TICKER, START_DATE, END_DATE)

if daily_df.empty:
    print("ERROR: Could not fetch daily data from Alpaca")
    sys.exit(1)

print(f"  Fetched {len(daily_df)} daily bars from {daily_df.iloc[0]['date']} to {daily_df.iloc[-1]['date']}")

# Add ATR
daily_df = calculate_atr(daily_df)

# ============================================================================
print("\n[2/7] Computing compression ranges...")

compression_df = compute_compression_ranges(daily_df, LOOKBACK_N)
print(f"  Computed {len(compression_df)} compression windows")

# Compute global compression threshold (bottom 20th percentile)
compression_threshold = np.percentile(compression_df['compression_range_pct'].dropna(), COMPRESSION_PERCENTILE)
print(f"  Compression threshold (bottom {COMPRESSION_PERCENTILE}th percentile): {compression_threshold:.2f}%")

# ============================================================================
print("\n[3/7] Identifying breakdowns and baseline events...")

breakdowns_df, baseline_df = identify_breakdowns_and_baseline(daily_df, compression_df, compression_threshold)
print(f"  Detected {len(breakdowns_df)} breakdown events")
print(f"  Detected {len(baseline_df)} baseline compression events (no breakdown)")

# ============================================================================
print("\n[4/7] Computing forward metrics for breakdowns...")

breakdown_events = []

for _, bd in breakdowns_df.iterrows():
    event = bd.to_dict()
    
    # Forward metrics
    fwd_metrics = compute_forward_metrics(daily_df, bd['index'], bd['close'], FORWARD_HORIZONS)
    event.update(fwd_metrics)
    
    # Range expansion metrics
    expansion_metrics = compute_range_expansion_metrics(daily_df, bd['index'])
    event.update(expansion_metrics)
    
    # ATR
    event['atr_14'] = daily_df.iloc[bd['index']]['atr']
    
    breakdown_events.append(event)

breakdown_events_df = pd.DataFrame(breakdown_events)
breakdown_csv = OUTPUT_DIR / "baba_compression_breakdowns_events.csv"
breakdown_events_df.to_csv(breakdown_csv, index=False)
print(f"  Saved: {breakdown_csv}")

# ============================================================================
print("\n[5/7] Computing forward metrics for baseline...")

baseline_events = []

for _, bl in baseline_df.iterrows():
    event = bl.to_dict()
    
    # Forward metrics
    fwd_metrics = compute_forward_metrics(daily_df, bl['index'], bl['close'], FORWARD_HORIZONS)
    event.update(fwd_metrics)
    
    # Range expansion metrics
    expansion_metrics = compute_range_expansion_metrics(daily_df, bl['index'])
    event.update(expansion_metrics)
    
    # ATR
    event['atr_14'] = daily_df.iloc[bl['index']]['atr']
    
    baseline_events.append(event)

baseline_events_df = pd.DataFrame(baseline_events)
baseline_csv = OUTPUT_DIR / "baba_compression_baseline_events.csv"
baseline_events_df.to_csv(baseline_csv, index=False)
print(f"  Saved: {baseline_csv}")

# ============================================================================
print("\n[6/7] Fetching intraday data and computing intraday metrics...")

intraday_results = []
intraday_coverage_count = 0

for _, bd in breakdowns_df.iterrows():
    date = bd['date']
    range_low = bd['range_low']
    
    print(f"  Fetching intraday for {date}...")
    intraday_df = fetch_intraday_bars(TICKER, date, INTRADAY_TIMEFRAME)
    
    if not intraday_df.empty and len(intraday_df) > 5:
        metrics = compute_intraday_breakdown_metrics(intraday_df, range_low, date)
        if metrics:
            intraday_results.append(metrics)
            intraday_coverage_count += 1
    else:
        # Add placeholder with NaNs
        intraday_results.append({
            'date': str(date),
            'range_low': range_low,
            'premarket_broke_below': np.nan,
            'rth_broke_below': np.nan,
            'rth_close_vs_range_low_pct': np.nan,
            'largest_5min_move_pct': np.nan,
            'largest_5min_move_time_ct': None
        })

intraday_df_final = pd.DataFrame(intraday_results)
intraday_csv = OUTPUT_DIR / "baba_compression_intraday_breakdown_metrics_5m.csv"
intraday_df_final.to_csv(intraday_csv, index=False)
print(f"  Saved: {intraday_csv}")
print(f"  Intraday coverage: {intraday_coverage_count}/{len(breakdowns_df)} ({intraday_coverage_count/len(breakdowns_df)*100:.1f}%)")

# ============================================================================
print("\n[7/7] Generating charts and report...")

# Chart 1: Forward returns boxplots
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
axes = axes.flatten()

for i, h in enumerate(FORWARD_HORIZONS):
    col = f'fwd_{h}d_return_pct'
    
    bd_data = breakdown_events_df[col].dropna()
    bl_data = baseline_events_df[col].dropna()
    
    if len(bd_data) > 0 or len(bl_data) > 0:
        data_to_plot = []
        labels = []
        
        if len(bd_data) > 0:
            data_to_plot.append(bd_data)
            labels.append('Breakdown')
        
        if len(bl_data) > 0:
            data_to_plot.append(bl_data)
            labels.append('Baseline')
        
        axes[i].boxplot(data_to_plot, labels=labels)
        axes[i].axhline(0, color='black', linestyle='--', linewidth=0.8)
        axes[i].set_ylabel('Return (%)')
        axes[i].set_title(f'+{h}d Forward Returns')
        axes[i].grid(True, alpha=0.3)

plt.tight_layout()
chart1_path = OUTPUT_DIR / "baba_breakdown_vs_baseline_forward_returns.png"
plt.savefig(chart1_path, dpi=150)
plt.close()
print(f"  Saved: {chart1_path}")

# Chart 2: MAE vs MFE scatter
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
axes = axes.flatten()

for i, h in enumerate(FORWARD_HORIZONS):
    mae_col = f'mae_{h}d_pct'
    mfe_col = f'mfe_{h}d_pct'
    
    if mae_col in breakdown_events_df.columns and mfe_col in breakdown_events_df.columns:
        bd_mae = breakdown_events_df[mae_col].dropna()
        bd_mfe = breakdown_events_df[mfe_col].dropna()
        
        if len(bd_mae) > 0 and len(bd_mfe) > 0:
            # Ensure same length
            min_len = min(len(bd_mae), len(bd_mfe))
            bd_mae = breakdown_events_df[mae_col].iloc[:min_len]
            bd_mfe = breakdown_events_df[mfe_col].iloc[:min_len]
            
            axes[i].scatter(bd_mae, bd_mfe, alpha=0.6, s=50)
            axes[i].axhline(0, color='black', linestyle='--', linewidth=0.8)
            axes[i].axvline(0, color='black', linestyle='--', linewidth=0.8)
            axes[i].plot([-20, 20], [-20, 20], 'r--', alpha=0.3, label='MAE=MFE')
            axes[i].set_xlabel('MAE (%)')
            axes[i].set_ylabel('MFE (%)')
            axes[i].set_title(f'+{h}d MAE vs MFE (Breakdowns)')
            axes[i].legend()
            axes[i].grid(True, alpha=0.3)

plt.tight_layout()
chart2_path = OUTPUT_DIR / "baba_breakdown_mae_mfe.png"
plt.savefig(chart2_path, dpi=150)
plt.close()
print(f"  Saved: {chart2_path}")

# Chart 3: Range expansion rate
expansion_rate = breakdown_events_df['range_expansion_flag'].mean() * 100
baseline_expansion_rate = baseline_events_df['range_expansion_flag'].mean() * 100

plt.figure(figsize=(8, 6))
plt.bar(['Breakdown Days', 'Baseline Days'], [expansion_rate, baseline_expansion_rate], 
        color=['red', 'gray'], alpha=0.7, edgecolor='black')
plt.ylabel('Range Expansion Rate (%)')
plt.title(f'Range Expansion Rate: Breakdown vs Baseline\n(>= {RANGE_EXPANSION_MULTIPLIER}x Median Prior 20-Day Range)')
plt.ylim(0, 100)
plt.grid(True, alpha=0.3, axis='y')
for i, (label, val) in enumerate([('Breakdown Days', expansion_rate), ('Baseline Days', baseline_expansion_rate)]):
    plt.text(i, val + 2, f'{val:.1f}%', ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
chart3_path = OUTPUT_DIR / "baba_breakdown_range_expansion_rate.png"
plt.savefig(chart3_path, dpi=150)
plt.close()
print(f"  Saved: {chart3_path}")

# Chart 4: Equity curves (median cumulative return)
plt.figure(figsize=(12, 6))

max_horizon = max(FORWARD_HORIZONS)

# Breakdown median cumulative
bd_cumulative = [0]
for h in range(1, max_horizon + 1):
    if h in FORWARD_HORIZONS:
        col = f'fwd_{h}d_return_pct'
        if col in breakdown_events_df.columns:
            median_ret = breakdown_events_df[col].median()
            bd_cumulative.append(median_ret)
        else:
            bd_cumulative.append(bd_cumulative[-1])
    else:
        bd_cumulative.append(bd_cumulative[-1])

# Baseline median cumulative
bl_cumulative = [0]
for h in range(1, max_horizon + 1):
    if h in FORWARD_HORIZONS:
        col = f'fwd_{h}d_return_pct'
        if col in baseline_events_df.columns:
            median_ret = baseline_events_df[col].median()
            bl_cumulative.append(median_ret)
        else:
            bl_cumulative.append(bl_cumulative[-1])
    else:
        bl_cumulative.append(bl_cumulative[-1])

plt.plot(range(max_horizon + 1), bd_cumulative, marker='o', linewidth=2, label='Breakdown (Median)', color='red')
plt.plot(range(max_horizon + 1), bl_cumulative, marker='s', linewidth=2, label='Baseline (Median)', color='gray')
plt.axhline(0, color='black', linestyle='--', linewidth=0.8)
plt.xlabel('Days After Event')
plt.ylabel('Median Cumulative Return (%)')
plt.title('Median Forward Return Paths: Breakdown vs Baseline')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
chart4_path = OUTPUT_DIR / "baba_breakdown_equity_curves_median.png"
plt.savefig(chart4_path, dpi=150)
plt.close()
print(f"  Saved: {chart4_path}")

# ============================================================================
# Generate Markdown Report
# ============================================================================

report_md = f"""# BABA Compression-Range Breakdown Study Report

**Study Type:** Compression-Range Breakdown Analysis  
**Execution Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Ticker:** {TICKER} (NYSE)  
**Study Period:** {START_DATE} to {END_DATE}  

---

## Study Design

### Objective

Analyze the follow-through behavior when BABA breaks down below a compressed trading range, comparing to baseline compression days without breakdown.

### Definitions

**Compression Window:**
- Lookback: {LOOKBACK_N} trading days ending at day t-1 (day before potential breakdown)
- `range_high` = max(High) over the {LOOKBACK_N}-day window
- `range_low` = min(Low) over the {LOOKBACK_N}-day window
- `compression_range_pct` = (range_high - range_low) / Close(t-1)

**Compression Qualification:**
- Day t is eligible if compression_range_pct is in the bottom {COMPRESSION_PERCENTILE}th percentile globally
- Threshold: {compression_threshold:.2f}% (computed from entire sample)

**Breakdown Trigger:**
- Qualified compression day where Close(t) < range_low

**Baseline:**
- Qualified compression day where Close(t) >= range_low (no breakdown)

---

## Data Source & Configuration

- **Data Source:** Alpaca (IEX feed)
- **Timezone:** Central Time (CT)
- **Sessions:** Premarket (3:00-8:29 CT) + RTH (8:30-15:00 CT)
- **Intraday Timeframe:** {INTRADAY_TIMEFRAME} bars
- **Forward Horizons:** +{', +'.join(map(str, FORWARD_HORIZONS))} trading days
- **Daily Bars Analyzed:** {len(daily_df)}

---

## Sample Sizes

- **Breakdown Events:** {len(breakdowns_df)}
- **Baseline Events:** {len(baseline_df)}
- **Intraday Coverage:** {intraday_coverage_count}/{len(breakdowns_df)} ({intraday_coverage_count/len(breakdowns_df)*100:.1f}%)

---

## Key Results

### A. Forward Returns: Breakdown vs Baseline

"""

# Forward return comparison table
for h in FORWARD_HORIZONS:
    col = f'fwd_{h}d_return_pct'
    
    bd_data = breakdown_events_df[col].dropna()
    bl_data = baseline_events_df[col].dropna()
    
    if len(bd_data) > 0:
        bd_mean = bd_data.mean()
        bd_median = bd_data.median()
        bd_hit_rate = (bd_data > 0).sum() / len(bd_data) * 100
    else:
        bd_mean = bd_median = bd_hit_rate = np.nan
    
    if len(bl_data) > 0:
        bl_mean = bl_data.mean()
        bl_median = bl_data.median()
        bl_hit_rate = (bl_data > 0).sum() / len(bl_data) * 100
    else:
        bl_mean = bl_median = bl_hit_rate = np.nan
    
    report_md += f"""
**+{h} Day:**
- Breakdown: Mean={bd_mean:.2f}%, Median={bd_median:.2f}%, Hit Rate={bd_hit_rate:.1f}%
- Baseline: Mean={bl_mean:.2f}%, Median={bl_median:.2f}%, Hit Rate={bl_hit_rate:.1f}%
- **Difference (BD - BL):** Mean={bd_mean - bl_mean:.2f}%, Median={bd_median - bl_median:.2f}%
"""

report_md += """
### B. Downside Skew (MAE vs MFE)

"""

for h in FORWARD_HORIZONS:
    mae_col = f'mae_{h}d_pct'
    mfe_col = f'mfe_{h}d_pct'
    
    if mae_col in breakdown_events_df.columns:
        bd_mae = breakdown_events_df[mae_col].median()
        bd_mfe = breakdown_events_df[mfe_col].median()
        
        report_md += f"**+{h} Day (Breakdown):** Median MAE={bd_mae:.2f}%, Median MFE={bd_mfe:.2f}%\n"

report_md += """
### C. Max Drawdown

"""

for h in FORWARD_HORIZONS:
    dd_col = f'max_dd_{h}d_pct'
    
    if dd_col in breakdown_events_df.columns:
        bd_dd = breakdown_events_df[dd_col].median()
        bl_dd = baseline_events_df[dd_col].median()
        
        report_md += f"**+{h} Day:** Breakdown Median={bd_dd:.2f}%, Baseline Median={bl_dd:.2f}%\n"

report_md += f"""
### D. Range Expansion on Breakdown Day

- **Breakdown Days with Range Expansion:** {expansion_rate:.1f}%
- **Baseline Days with Range Expansion:** {baseline_expansion_rate:.1f}%
- **Expansion Threshold:** >= {RANGE_EXPANSION_MULTIPLIER}x median prior 20-day range

**Interpretation:** {"Breakdowns tend to occur with range expansion." if expansion_rate > baseline_expansion_rate else "Breakdowns do not consistently show range expansion."}

---

## Intraday Breakdown Behavior

"""

if intraday_coverage_count > 0:
    # Premarket breakdown rate
    pm_broke = intraday_df_final['premarket_broke_below'].sum()
    pm_total = intraday_df_final['premarket_broke_below'].notna().sum()
    
    # RTH breakdown rate
    rth_broke = intraday_df_final['rth_broke_below'].sum()
    rth_total = intraday_df_final['rth_broke_below'].notna().sum()
    
    # RTH close vs range_low
    rth_close_mean = intraday_df_final['rth_close_vs_range_low_pct'].mean()
    
    report_md += f"""
- **Premarket Breakdown Rate:** {pm_broke}/{pm_total} ({pm_broke/pm_total*100:.1f}%) traded below range_low
- **RTH Breakdown Rate:** {rth_broke}/{rth_total} ({rth_broke/rth_total*100:.1f}%) traded below range_low
- **RTH Close vs Range Low:** Mean {rth_close_mean:+.2f}% relative to range_low
- **Largest 5-Min Moves:** Available in intraday CSV

"""
else:
    report_md += "- **No intraday data available** for historical breakdown dates\n\n"

report_md += """
---

## Interpretation & Key Insights

"""

# Calculate key insights
bd_1d = breakdown_events_df['fwd_1d_return_pct'].median()
bl_1d = baseline_events_df['fwd_1d_return_pct'].median()
bd_10d = breakdown_events_df['fwd_10d_return_pct'].median()
bl_10d = baseline_events_df['fwd_10d_return_pct'].median()

report_md += f"""
1. **Immediate Follow-Through (+1d):**
   - Breakdown median: {bd_1d:.2f}%
   - Baseline median: {bl_1d:.2f}%
   - {"Breakdowns underperform baseline immediately." if bd_1d < bl_1d else "Breakdowns do not underperform baseline immediately."}

2. **Medium-Term Performance (+10d):**
   - Breakdown median: {bd_10d:.2f}%
   - Baseline median: {bl_10d:.2f}%
   - {"Breakdowns continue to underperform." if bd_10d < bl_10d else "Breakdowns show relative strength over 10 days."}

3. **Range Expansion:**
   - {expansion_rate:.1f}% of breakdowns occur with range expansion
   - {"This suggests breakdowns are accompanied by volatility spikes." if expansion_rate > 50 else "Range expansion is not a reliable characteristic."}

4. **Downside Skew:**
   - MAE typically exceeds MFE magnitude on breakdown days
   - {"Significant downside asymmetry present." if breakdown_events_df['mae_10d_pct'].median() < -5 else "Moderate downside risk."}

---

## Limitations & Failure Modes

1. **Sample Size:** {len(breakdowns_df)} breakdown events may not be sufficient for robust statistical inference
2. **Compression Definition:** Bottom {COMPRESSION_PERCENTILE}th percentile is a global static threshold; market regimes change over time
3. **No Context Filters:** Does not account for trend, sector performance, or broader market conditions
4. **Survivorship:** BABA has been volatile due to regulatory/geopolitical factors that may not apply to other tickers
5. **Historical Period:** {START_DATE} to {END_DATE} includes multiple regime changes (COVID, China tech crackdown, etc.)
6. **Intraday Coverage:** Only {intraday_coverage_count/len(breakdowns_df)*100:.1f}% of events have intraday data

---

## Outputs

All outputs saved in `outputs/`:

1. `baba_compression_breakdowns_events.csv` — Breakdown events with forward metrics
2. `baba_compression_baseline_events.csv` — Baseline compression events with forward metrics
3. `baba_compression_intraday_breakdown_metrics_5m.csv` — Intraday 5-min metrics
4. `baba_breakdown_vs_baseline_forward_returns.png` — Forward return distributions
5. `baba_breakdown_mae_mfe.png` — MAE vs MFE scatter plots
6. `baba_breakdown_range_expansion_rate.png` — Range expansion comparison
7. `baba_breakdown_equity_curves_median.png` — Median return paths
8. `baba_study2_report.md` — This report

---

**Study Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

report_path = OUTPUT_DIR / "baba_study2_report.md"
with open(report_path, 'w') as f:
    f.write(report_md)

print(f"  Saved: {report_path}")

# ============================================================================
# CONSOLE SUMMARY
# ============================================================================

print("\n" + "="*80)
print("EXECUTION COMPLETE")
print("="*80)
print("\nConsole Summary:")
print(f"  Ticker: {TICKER}")
print(f"  Period: {START_DATE} to {END_DATE}")
print(f"  Compression Threshold: {compression_threshold:.2f}%")
print(f"  Breakdown Events: {len(breakdowns_df)}")
print(f"  Baseline Events: {len(baseline_df)}")
print()

print("Median Forward Returns:")
print("  Horizon | Breakdown | Baseline | Difference")
print("  --------|-----------|----------|------------")
for h in FORWARD_HORIZONS:
    col = f'fwd_{h}d_return_pct'
    bd_med = breakdown_events_df[col].median()
    bl_med = baseline_events_df[col].median()
    diff = bd_med - bl_med
    print(f"  +{h:2}d    | {bd_med:+7.2f}%  | {bl_med:+7.2f}% | {diff:+7.2f}%")

print()
print("Median MAE/MFE (Breakdown):")
for h in [1, 5, 10, 20]:
    mae_col = f'mae_{h}d_pct'
    mfe_col = f'mfe_{h}d_pct'
    if mae_col in breakdown_events_df.columns:
        mae = breakdown_events_df[mae_col].median()
        mfe = breakdown_events_df[mfe_col].median()
        print(f"  +{h:2}d: MAE={mae:+.2f}%, MFE={mfe:+.2f}%")

print()
print("Median Max Drawdown (Breakdown vs Baseline):")
for h in [1, 5, 10, 20]:
    dd_col = f'max_dd_{h}d_pct'
    if dd_col in breakdown_events_df.columns:
        bd_dd = breakdown_events_df[dd_col].median()
        bl_dd = baseline_events_df[dd_col].median()
        print(f"  +{h:2}d: Breakdown={bd_dd:+.2f}%, Baseline={bl_dd:+.2f}%")

print()
print(f"Range Expansion Rate:")
print(f"  Breakdown Days: {expansion_rate:.1f}%")
print(f"  Baseline Days: {baseline_expansion_rate:.1f}%")

print()
print("Output Files:")
print(f"  {breakdown_csv}")
print(f"  {baseline_csv}")
print(f"  {intraday_csv}")
print(f"  {chart1_path}")
print(f"  {chart2_path}")
print(f"  {chart3_path}")
print(f"  {chart4_path}")
print(f"  {report_path}")
print()
print("="*80)

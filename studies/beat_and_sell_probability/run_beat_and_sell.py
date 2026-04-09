"""
╔══════════════════════════════════════════════════════════════════════╗
║  QUANTLAB STUDY: BEAT & SELL PROBABILITY — NARRATIVE CEILING FADE  ║
║  Designed by: Claude (Senior Analyst) for Lakeem's War Room        ║
║  Date: February 26, 2026                                          ║
║  Hypothesis: When mega-caps beat earnings into structural          ║
║  distribution (no new highs, RS declining, beat compression),      ║
║  the probability of a post-earnings FADE is significantly          ║
║  elevated — creating a tradeable short setup.                      ║
╚══════════════════════════════════════════════════════════════════════╝

WHAT THIS STUDY DOES:
1. Pulls daily price data for 25 mega-cap stocks over 2020-2026
2. Identifies earnings dates via overnight gap detection (>2% gap = earnings proxy)
3. For each earnings gap-up event, measures 5 PRE-EARNINGS structural conditions:
   - Days since all-time high (distribution signal)
   - Price range compression (stuck in a box)
   - Trailing 20-day relative strength vs SPY (RS momentum)
   - Consecutive gap-up earnings streak (beat fatigue)
   - Pre-earnings 5-day drift (buy-the-rumor already happened)
4. Measures POST-EARNINGS outcomes: day-of fade, +1d, +3d, +5d returns from open
5. Splits events into "CLEAN" (no distribution signals) vs "NARRATIVE CEILING"
   (multiple distribution signals present) and compares outcomes
6. Produces win rates, expectancy, and a composite "Beat & Sell Probability Score"

SUCCESS CRITERIA:
- Minimum 50 "Narrative Ceiling" events identified
- Statistically significant difference in fade rates between clean vs ceiling
- Clear, actionable thresholds for each condition
- Real examples with dates and tickers for pattern recognition
"""

import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from shared.data_router import DataRouter
from shared.chart_builder import ChartBuilder

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

STUDY_NAME = "beat_and_sell_probability"
STUDY_DIR = Path(r'C:\QuantLab\Data_Lab\studies') / STUDY_NAME
OUTPUT_DIR = STUDY_DIR / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"

# Create directories
for d in [STUDY_DIR, OUTPUT_DIR, CHARTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Mega-cap universe — the stocks where "narrative ceiling" dynamics exist
# These are the names big enough that institutional positioning and
# narrative regime dominate post-earnings price action
UNIVERSE = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOG", "META", "TSLA",
    "AVGO", "AMD", "CRM", "NFLX", "ADBE", "ORCL", "COST",
    "LLY", "UNH", "V", "MA", "JPM", "HD",
    "NOW", "UBER", "PLTR", "PANW", "SNOW"
]

BENCHMARK = "SPY"

# Date range — 5+ years of earnings cycles
START_DATE = "2020-01-01"
END_DATE = "2026-02-26"

# Earnings detection parameters
# We detect earnings via overnight gaps. A gap > threshold on high volume
# is almost certainly an earnings reaction (or major catalyst — both valid)
GAP_UP_THRESHOLD = 0.02      # 2% gap up = likely positive earnings reaction
GAP_DOWN_THRESHOLD = -0.02   # 2% gap down = likely negative reaction
VOLUME_SPIKE_MULT = 1.5      # Volume must be 1.5x 20-day average

# Structural condition thresholds (what defines "narrative ceiling")
DAYS_SINCE_ATH_THRESHOLD = 60       # >60 days since ATH = distribution
RANGE_COMPRESSION_WINDOW = 60       # Look at 60-day price range
RANGE_COMPRESSION_THRESHOLD = 0.85  # Price within top 85% of range = compressed
RS_WEAKNESS_THRESHOLD = 0.0         # RS vs SPY trailing 20d <= 0 = weak RS
PRE_DRIFT_THRESHOLD = 0.03          # >3% gain in 5 days pre-earnings = front-run
CONSEC_BEAT_THRESHOLD = 3           # 3+ consecutive gap-up earnings = fatigue

# Forward return windows
FORWARD_WINDOWS = [0, 1, 3, 5, 10]  # day-of (open to close), +1d, +3d, +5d, +10d

print("=" * 70)
print("BEAT & SELL PROBABILITY STUDY — NARRATIVE CEILING FADE")
print("=" * 70)
print(f"Universe: {len(UNIVERSE)} mega-cap stocks")
print(f"Period: {START_DATE} to {END_DATE}")
print(f"Gap-up threshold: >{GAP_UP_THRESHOLD*100:.0f}%")
print()

# ═══════════════════════════════════════════════════════
# PHASE 1: DATA COLLECTION
# ═══════════════════════════════════════════════════════

print("PHASE 1: Pulling price data...")
print("-" * 40)

all_data = {}
failed_tickers = []

# Pull benchmark first
try:
    spy_df = DataRouter.get_price_data(
        ticker=BENCHMARK,
        start_date=START_DATE,
        end_date=END_DATE,
        timeframe='daily',
        study_type='indicator'
    )
    spy_df = spy_df.sort_index()
    spy_df['spy_return_20d'] = spy_df['Close'].pct_change(20)
    spy_df['spy_return_1d'] = spy_df['Close'].pct_change(1)
    print(f"  ✅ {BENCHMARK}: {len(spy_df)} bars loaded")
except Exception as e:
    print(f"  ❌ CRITICAL: Failed to load {BENCHMARK}: {e}")
    print("  Cannot proceed without benchmark data. Exiting.")
    raise SystemExit(1)

# Pull each stock
for ticker in UNIVERSE:
    try:
        df = DataRouter.get_price_data(
            ticker=ticker,
            start_date=START_DATE,
            end_date=END_DATE,
            timeframe='daily',
            study_type='indicator'
        )
        df = df.sort_index()
        if len(df) < 252:  # Need at least 1 year
            print(f"  ⚠️ {ticker}: Only {len(df)} bars — skipping (need 252+)")
            failed_tickers.append(ticker)
            continue
        all_data[ticker] = df
        print(f"  ✅ {ticker}: {len(df)} bars loaded")
    except Exception as e:
        print(f"  ❌ {ticker}: Failed — {e}")
        failed_tickers.append(ticker)

print(f"\nLoaded: {len(all_data)}/{len(UNIVERSE)} tickers")
if failed_tickers:
    print(f"Failed: {failed_tickers}")
print()

# ═══════════════════════════════════════════════════════
# PHASE 2: EARNINGS EVENT DETECTION
# ═══════════════════════════════════════════════════════

print("PHASE 2: Detecting earnings events via overnight gaps...")
print("-" * 40)

all_events = []

for ticker, df in all_data.items():
    df = df.copy()

    # Calculate overnight gap: today's open vs yesterday's close
    df['prev_close'] = df['Close'].shift(1)
    df['overnight_gap'] = (df['Open'] - df['prev_close']) / df['prev_close']

    # Volume spike detection
    df['vol_ma20'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_ma20']

    # Relative strength vs SPY (trailing 20 days)
    df['return_20d'] = df['Close'].pct_change(20)
    df = df.join(spy_df[['spy_return_20d']], how='left')
    df['rs_vs_spy_20d'] = df['return_20d'] - df['spy_return_20d']

    # Rolling ATH and days since ATH
    df['rolling_ath'] = df['High'].expanding().max()
    df['at_ath'] = df['High'] >= df['rolling_ath'] * 0.99  # Within 1% of ATH
    df['days_since_ath'] = 0
    last_ath_idx = 0
    for i in range(len(df)):
        if df['at_ath'].iloc[i]:
            last_ath_idx = i
        df.iloc[i, df.columns.get_loc('days_since_ath')] = i - last_ath_idx

    # 60-day price range compression
    df['high_60d'] = df['High'].rolling(RANGE_COMPRESSION_WINDOW).max()
    df['low_60d'] = df['Low'].rolling(RANGE_COMPRESSION_WINDOW).min()
    df['range_60d'] = (df['high_60d'] - df['low_60d']) / df['low_60d']
    df['price_in_range'] = (df['Close'] - df['low_60d']) / (df['high_60d'] - df['low_60d'])

    # Pre-earnings 5-day drift
    df['pre_drift_5d'] = df['Close'].pct_change(5)

    # Day-of return (open to close) — this captures the FADE
    df['day_of_return'] = (df['Close'] - df['Open']) / df['Open']

    # Forward returns from the OPEN (not the close — we're measuring gap fade)
    for window in FORWARD_WINDOWS:
        if window == 0:
            df[f'fwd_return_{window}d'] = df['day_of_return']  # open to close same day
        else:
            future_close = df['Close'].shift(-window)
            df[f'fwd_return_{window}d'] = (future_close - df['Open']) / df['Open']

    # Detect gap-up events (likely positive earnings)
    # Build a tz-aware cutoff that matches the index coming from Alpaca (UTC)
    _cutoff = pd.Timestamp(START_DATE) + pd.Timedelta(days=252)
    if df.index.tz is not None:
        _cutoff = _cutoff.tz_localize(df.index.tz)

    gap_up_mask = (
        (df['overnight_gap'] >= GAP_UP_THRESHOLD) &
        (df['vol_ratio'] >= VOLUME_SPIKE_MULT) &
        (df.index >= _cutoff)  # Need 1yr history
    )

    gap_up_events = df[gap_up_mask].copy()

    # Track consecutive gap-up earnings streak for each event
    # Look back through prior gap-up events for this ticker
    ticker_gap_dates = gap_up_events.index.tolist()

    for idx, row in gap_up_events.iterrows():
        # Count consecutive prior gap-up earnings (within ~100 trading days of each other)
        streak = 1
        current_pos = ticker_gap_dates.index(idx)
        for prev_pos in range(current_pos - 1, -1, -1):
            prev_date = ticker_gap_dates[prev_pos]
            days_between = (idx - prev_date).days
            if 45 <= days_between <= 120:  # Roughly one quarter apart
                streak += 1
                current_pos = prev_pos
            else:
                break

        event = {
            'ticker': ticker,
            'date': idx,
            'overnight_gap': row['overnight_gap'],
            'volume_ratio': row['vol_ratio'],
            'days_since_ath': row['days_since_ath'],
            'range_60d': row['range_60d'],
            'price_in_range': row['price_in_range'],
            'rs_vs_spy_20d': row['rs_vs_spy_20d'],
            'pre_drift_5d': row['pre_drift_5d'],
            'consecutive_beat_streak': streak,
            'day_of_return': row['day_of_return'],
        }

        # Add forward returns
        for window in FORWARD_WINDOWS:
            col = f'fwd_return_{window}d'
            event[col] = row[col] if pd.notna(row[col]) else np.nan

        all_events.append(event)

events_df = pd.DataFrame(all_events)
print(f"\nTotal gap-up earnings events detected: {len(events_df)}")
print(f"Unique tickers with events: {events_df['ticker'].nunique()}")
print(f"Events per ticker (avg): {len(events_df) / events_df['ticker'].nunique():.1f}")

# Show distribution
print(f"\nGap size distribution:")
print(f"  Mean gap: +{events_df['overnight_gap'].mean()*100:.1f}%")
print(f"  Median gap: +{events_df['overnight_gap'].median()*100:.1f}%")
print(f"  Max gap: +{events_df['overnight_gap'].max()*100:.1f}%")
print()

# ═══════════════════════════════════════════════════════
# PHASE 3: NARRATIVE CEILING CLASSIFICATION
# ═══════════════════════════════════════════════════════

print("PHASE 3: Classifying events — Clean vs Narrative Ceiling...")
print("-" * 40)

# Score each event on 5 structural conditions
# Each condition that's TRUE adds 1 to the "ceiling score"

events_df['cond_distribution'] = (
    events_df['days_since_ath'] >= DAYS_SINCE_ATH_THRESHOLD
).astype(int)

events_df['cond_range_compressed'] = (
    events_df['range_60d'] <= 0.15  # 60-day range is tight (<15%)
).astype(int)

events_df['cond_rs_weak'] = (
    events_df['rs_vs_spy_20d'] <= RS_WEAKNESS_THRESHOLD
).astype(int)

events_df['cond_front_run'] = (
    events_df['pre_drift_5d'] >= PRE_DRIFT_THRESHOLD
).astype(int)

events_df['cond_beat_fatigue'] = (
    events_df['consecutive_beat_streak'] >= CONSEC_BEAT_THRESHOLD
).astype(int)

# Composite ceiling score (0-5)
events_df['ceiling_score'] = (
    events_df['cond_distribution'] +
    events_df['cond_range_compressed'] +
    events_df['cond_rs_weak'] +
    events_df['cond_front_run'] +
    events_df['cond_beat_fatigue']
)

# Classification
events_df['regime'] = 'CLEAN'
events_df.loc[events_df['ceiling_score'] >= 1, 'regime'] = 'MILD_CEILING'
events_df.loc[events_df['ceiling_score'] >= 2, 'regime'] = 'MODERATE_CEILING'
events_df.loc[events_df['ceiling_score'] >= 3, 'regime'] = 'NARRATIVE_CEILING'
events_df.loc[events_df['ceiling_score'] >= 4, 'regime'] = 'EXTREME_CEILING'

print("Event distribution by regime:")
regime_counts = events_df['regime'].value_counts().sort_index()
for regime, count in regime_counts.items():
    print(f"  {regime}: {count} events")

print(f"\nCondition hit rates:")
print(f"  Distribution (>{DAYS_SINCE_ATH_THRESHOLD}d since ATH): "
      f"{events_df['cond_distribution'].mean()*100:.1f}%")
print(f"  Range compressed (<15% 60d range): "
      f"{events_df['cond_range_compressed'].mean()*100:.1f}%")
print(f"  RS weakness (RS vs SPY <=0): "
      f"{events_df['cond_rs_weak'].mean()*100:.1f}%")
print(f"  Front-run (>3% 5d pre-drift): "
      f"{events_df['cond_front_run'].mean()*100:.1f}%")
print(f"  Beat fatigue (3+ consec beats): "
      f"{events_df['cond_beat_fatigue'].mean()*100:.1f}%")
print()

# ═══════════════════════════════════════════════════════
# PHASE 4: OUTCOME ANALYSIS
# ═══════════════════════════════════════════════════════

print("PHASE 4: Measuring outcomes — Does the ceiling predict fades?")
print("-" * 40)

# Drop events with missing forward returns
analysis_df = events_df.dropna(subset=['fwd_return_5d']).copy()
print(f"Events with complete forward data: {len(analysis_df)}")

# Define "fade" as: stock opened gap-up but closed BELOW the open (day-of)
analysis_df['day_of_fade'] = (analysis_df['day_of_return'] < 0).astype(int)

# Define "5-day fade" as: stock is below earnings-day open after 5 days
analysis_df['fwd_5d_fade'] = (analysis_df['fwd_return_5d'] < 0).astype(int)

# ── Core comparison: CLEAN vs NARRATIVE CEILING ──

def calc_group_stats(group_df, label):
    """Calculate comprehensive stats for an event group."""
    n = len(group_df)
    if n == 0:
        return None

    stats = {'label': label, 'n': n}

    # Day-of fade rate
    stats['day_fade_rate'] = group_df['day_of_fade'].mean()

    # Forward return stats
    for window in FORWARD_WINDOWS:
        col = f'fwd_return_{window}d'
        valid = group_df[col].dropna()
        if len(valid) > 0:
            stats[f'mean_{window}d'] = valid.mean()
            stats[f'median_{window}d'] = valid.median()
            stats[f'win_rate_{window}d'] = (valid > 0).mean()
            stats[f'fade_rate_{window}d'] = (valid < 0).mean()
            stats[f'avg_win_{window}d'] = valid[valid > 0].mean() if (valid > 0).any() else 0
            stats[f'avg_loss_{window}d'] = valid[valid < 0].mean() if (valid < 0).any() else 0

    # Expectancy (using 5d as primary)
    col_5d = 'fwd_return_5d'
    valid_5d = group_df[col_5d].dropna()
    if len(valid_5d) > 0:
        wins = valid_5d[valid_5d > 0]
        losses = valid_5d[valid_5d < 0]
        wr = len(wins) / len(valid_5d) if len(valid_5d) > 0 else 0
        avg_w = wins.mean() if len(wins) > 0 else 0
        avg_l = abs(losses.mean()) if len(losses) > 0 else 0
        stats['expectancy_5d'] = (wr * avg_w) - ((1 - wr) * avg_l)

    return stats

# Group analysis
print("\n" + "=" * 70)
print("CORE RESULTS: GAP-UP EARNINGS OUTCOMES BY REGIME")
print("=" * 70)

results = []
for regime in ['CLEAN', 'MILD_CEILING', 'MODERATE_CEILING',
               'NARRATIVE_CEILING', 'EXTREME_CEILING']:
    group = analysis_df[analysis_df['regime'] == regime]
    if len(group) > 0:
        stats = calc_group_stats(group, regime)
        if stats:
            results.append(stats)

# Also do binary split: ceiling_score < 2 vs >= 2
clean_group = analysis_df[analysis_df['ceiling_score'] < 2]
ceiling_group = analysis_df[analysis_df['ceiling_score'] >= 2]

results.append(calc_group_stats(clean_group, '── COMBINED: CLEAN (0-1) ──'))
results.append(calc_group_stats(ceiling_group, '── COMBINED: CEILING (2+) ──'))

# Also the really extreme: 3+
extreme_group = analysis_df[analysis_df['ceiling_score'] >= 3]
if len(extreme_group) > 0:
    results.append(calc_group_stats(extreme_group, '── EXTREME CEILING (3+) ──'))

results_df = pd.DataFrame(results)

# Print formatted results
for _, row in results_df.iterrows():
    print(f"\n{'─' * 50}")
    print(f"  {row['label']}  (n={row['n']:.0f})")
    print(f"{'─' * 50}")
    print(f"  Day-of fade rate (open→close RED): {row.get('day_fade_rate', 0)*100:.1f}%")

    for window in FORWARD_WINDOWS:
        wr = row.get(f'win_rate_{window}d', 0)
        mean_r = row.get(f'mean_{window}d', 0)
        median_r = row.get(f'median_{window}d', 0)
        print(f"  +{window}d: Win Rate {wr*100:.1f}% | "
              f"Mean {mean_r*100:+.2f}% | Median {median_r*100:+.2f}%")

    exp = row.get('expectancy_5d', 0)
    print(f"  5-Day Expectancy: {exp*100:+.3f}%")

# ═══════════════════════════════════════════════════════
# PHASE 5: INDIVIDUAL CONDITION POWER
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("CONDITION POWER ANALYSIS: Which conditions predict fades best?")
print("=" * 70)

conditions = [
    ('cond_distribution', f'Days Since ATH > {DAYS_SINCE_ATH_THRESHOLD}'),
    ('cond_range_compressed', 'Range Compressed (<15% 60d)'),
    ('cond_rs_weak', 'RS vs SPY Weak (<=0)'),
    ('cond_front_run', 'Pre-Earnings Front-Run (>3% 5d)'),
    ('cond_beat_fatigue', 'Beat Fatigue (3+ Consecutive)'),
]

condition_results = []
for col, label in conditions:
    present = analysis_df[analysis_df[col] == 1]
    absent = analysis_df[analysis_df[col] == 0]

    if len(present) >= 5:
        p_fade = present['day_of_fade'].mean()
        a_fade = absent['day_of_fade'].mean()
        p_5d = present['fwd_return_5d'].mean()
        a_5d = absent['fwd_return_5d'].mean()
        lift = p_fade - a_fade

        print(f"\n  {label}")
        print(f"    Present (n={len(present)}): Day fade {p_fade*100:.1f}% | "
              f"5d mean {p_5d*100:+.2f}%")
        print(f"    Absent  (n={len(absent)}):  Day fade {a_fade*100:.1f}% | "
              f"5d mean {a_5d*100:+.2f}%")
        print(f"    FADE LIFT: {lift*100:+.1f} percentage points")

        condition_results.append({
            'condition': label,
            'n_present': len(present),
            'fade_rate_present': p_fade,
            'fade_rate_absent': a_fade,
            'fade_lift': lift,
            'mean_5d_present': p_5d,
            'mean_5d_absent': a_5d,
        })

condition_power_df = pd.DataFrame(condition_results)

# ═══════════════════════════════════════════════════════
# PHASE 6: TICKER-LEVEL ANALYSIS (WHO DOES THIS MOST?)
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("TICKER BREAKDOWN: Which stocks show the strongest Beat & Sell pattern?")
print("=" * 70)

ticker_stats = []
for ticker in analysis_df['ticker'].unique():
    t_df = analysis_df[analysis_df['ticker'] == ticker]
    ceiling_events = t_df[t_df['ceiling_score'] >= 2]

    if len(ceiling_events) >= 2:  # Need at least 2 ceiling events
        stats = {
            'ticker': ticker,
            'total_gap_ups': len(t_df),
            'ceiling_events': len(ceiling_events),
            'ceiling_pct': len(ceiling_events) / len(t_df),
            'overall_day_fade': t_df['day_of_fade'].mean(),
            'ceiling_day_fade': ceiling_events['day_of_fade'].mean(),
            'ceiling_mean_5d': ceiling_events['fwd_return_5d'].mean(),
            'ceiling_mean_day': ceiling_events['fwd_return_0d'].mean(),
        }
        ticker_stats.append(stats)

ticker_df = pd.DataFrame(ticker_stats)
if len(ticker_df) > 0:
    ticker_df = ticker_df.sort_values('ceiling_day_fade', ascending=False)

    for _, row in ticker_df.iterrows():
        print(f"  {row['ticker']:6s} | Gap-ups: {row['total_gap_ups']:.0f} | "
              f"Ceiling events: {row['ceiling_events']:.0f} | "
              f"Ceiling fade rate: {row['ceiling_day_fade']*100:.1f}% | "
              f"Ceiling 5d mean: {row['ceiling_mean_5d']*100:+.2f}%")

# ═══════════════════════════════════════════════════════
# PHASE 7: REAL EXAMPLES — SHOW ME THE TRADES
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("REAL EXAMPLES: Highest Ceiling Score Events")
print("=" * 70)

# Show top ceiling events with outcomes
top_ceiling = analysis_df.nlargest(20, 'ceiling_score').sort_values(
    'ceiling_score', ascending=False
)

for _, row in top_ceiling.iterrows():
    fade_emoji = "🔴" if row['day_of_return'] < 0 else "🟢"
    print(f"\n  {fade_emoji} {row['ticker']} — {row['date'].strftime('%Y-%m-%d')}")
    print(f"     Gap: +{row['overnight_gap']*100:.1f}% | "
          f"Ceiling Score: {row['ceiling_score']:.0f}/5")
    print(f"     Days since ATH: {row['days_since_ath']:.0f} | "
          f"RS vs SPY: {row['rs_vs_spy_20d']*100:+.1f}% | "
          f"Pre-drift: {row['pre_drift_5d']*100:+.1f}%")
    print(f"     Day-of: {row['day_of_return']*100:+.2f}% | "
          f"5d: {row['fwd_return_5d']*100:+.2f}%")

# ═══════════════════════════════════════════════════════
# PHASE 8: NVDA-SPECIFIC DEEP DIVE
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("NVDA DEEP DIVE: Every Gap-Up Earnings Event")
print("=" * 70)

nvda_events = analysis_df[analysis_df['ticker'] == 'NVDA'].sort_values('date')
if len(nvda_events) > 0:
    for _, row in nvda_events.iterrows():
        fade_emoji = "🔴" if row['day_of_return'] < 0 else "🟢"
        print(f"\n  {fade_emoji} {row['date'].strftime('%Y-%m-%d')} | "
              f"Gap: +{row['overnight_gap']*100:.1f}%")
        print(f"     Ceiling: {row['ceiling_score']:.0f}/5 | "
              f"ATH: {row['days_since_ath']:.0f}d ago | "
              f"RS: {row['rs_vs_spy_20d']*100:+.1f}% | "
              f"Streak: {row['consecutive_beat_streak']:.0f}")
        print(f"     Day: {row['day_of_return']*100:+.2f}% | "
              f"5d: {row['fwd_return_5d']*100:+.2f}% | "
              f"10d: {row.get('fwd_return_10d', np.nan)*100:+.2f}%")

    # NVDA ceiling vs clean comparison
    nvda_clean = nvda_events[nvda_events['ceiling_score'] < 2]
    nvda_ceiling = nvda_events[nvda_events['ceiling_score'] >= 2]
    print(f"\n  NVDA Summary:")
    print(f"    Clean events (score 0-1): n={len(nvda_clean)}, "
          f"day fade rate: {nvda_clean['day_of_fade'].mean()*100:.1f}%")
    print(f"    Ceiling events (score 2+): n={len(nvda_ceiling)}, "
          f"day fade rate: {nvda_ceiling['day_of_fade'].mean()*100:.1f}%")
else:
    print("  No NVDA gap-up events found in the dataset.")

# ═══════════════════════════════════════════════════════
# PHASE 9: CHARTS
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PHASE 9: Generating charts...")
print("-" * 40)

# Chart 1: Fade rate by ceiling score (bar chart)
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # Fade rates by ceiling score
    score_groups = analysis_df.groupby('ceiling_score').agg(
        n=('day_of_fade', 'count'),
        day_fade_rate=('day_of_fade', 'mean'),
        mean_5d_return=('fwd_return_5d', 'mean'),
        mean_day_return=('fwd_return_0d', 'mean'),
    ).reset_index()

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            'Day-of Fade Rate by Ceiling Score (Higher = More Fades)',
            'Average 5-Day Return from Open by Ceiling Score'
        ],
        vertical_spacing=0.15
    )

    colors = ['#00C853', '#8BC34A', '#FFC107', '#FF9800', '#FF5722', '#D50000']

    fig.add_trace(
        go.Bar(
            x=[f"Score {int(s)} (n={int(n)})" for s, n in
               zip(score_groups['ceiling_score'], score_groups['n'])],
            y=score_groups['day_fade_rate'] * 100,
            marker_color=[colors[min(int(s), 5)] for s in score_groups['ceiling_score']],
            text=[f"{v:.1f}%" for v in score_groups['day_fade_rate'] * 100],
            textposition='outside',
            name='Day Fade Rate'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            x=[f"Score {int(s)} (n={int(n)})" for s, n in
               zip(score_groups['ceiling_score'], score_groups['n'])],
            y=score_groups['mean_5d_return'] * 100,
            marker_color=[colors[min(int(s), 5)] for s in score_groups['ceiling_score']],
            text=[f"{v:+.2f}%" for v in score_groups['mean_5d_return'] * 100],
            textposition='outside',
            name='Mean 5d Return'
        ),
        row=2, col=1
    )

    fig.update_layout(
        title=dict(
            text='BEAT & SELL PROBABILITY: Narrative Ceiling Score vs Outcomes',
            font=dict(size=18)
        ),
        template='plotly_dark',
        height=800,
        showlegend=False
    )
    fig.update_yaxes(title_text="Fade Rate (%)", row=1, col=1)
    fig.update_yaxes(title_text="Avg 5d Return (%)", row=2, col=1)

    chart_path = CHARTS_DIR / "ceiling_score_vs_outcomes.html"
    fig.write_html(str(chart_path))
    print(f"  ✅ Chart saved: {chart_path}")

except Exception as e:
    print(f"  ❌ Chart 1 failed: {e}")

# Chart 2: Condition power comparison
try:
    if len(condition_power_df) > 0:
        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            name='Fade Rate WITH Condition',
            x=condition_power_df['condition'],
            y=condition_power_df['fade_rate_present'] * 100,
            marker_color='#FF5722',
            text=[f"{v:.1f}%" for v in condition_power_df['fade_rate_present'] * 100],
            textposition='outside'
        ))

        fig2.add_trace(go.Bar(
            name='Fade Rate WITHOUT Condition',
            x=condition_power_df['condition'],
            y=condition_power_df['fade_rate_absent'] * 100,
            marker_color='#4CAF50',
            text=[f"{v:.1f}%" for v in condition_power_df['fade_rate_absent'] * 100],
            textposition='outside'
        ))

        fig2.update_layout(
            title='Condition Power: Which Factors Predict Post-Earnings Fades?',
            template='plotly_dark',
            barmode='group',
            height=600,
            yaxis_title='Day-of Fade Rate (%)',
            legend=dict(x=0.7, y=0.95)
        )

        chart_path = CHARTS_DIR / "condition_power.html"
        fig2.write_html(str(chart_path))
        print(f"  ✅ Chart saved: {chart_path}")

except Exception as e:
    print(f"  ❌ Chart 2 failed: {e}")

# Chart 3: NVDA timeline — ceiling score over earnings history
try:
    if len(nvda_events) > 0:
        fig3 = go.Figure()

        colors_nvda = ['🟢' if r > 0 else '🔴' for r in nvda_events['day_of_return']]
        marker_colors = ['#00C853' if r > 0 else '#FF5722'
                        for r in nvda_events['day_of_return']]

        fig3.add_trace(go.Scatter(
            x=nvda_events['date'],
            y=nvda_events['ceiling_score'],
            mode='markers+lines',
            marker=dict(
                size=15,
                color=marker_colors,
                line=dict(width=2, color='white')
            ),
            text=[f"Gap: +{g*100:.1f}%<br>Day: {d*100:+.1f}%<br>"
                  f"5d: {f*100:+.1f}%<br>Score: {s:.0f}"
                  for g, d, f, s in zip(
                      nvda_events['overnight_gap'],
                      nvda_events['day_of_return'],
                      nvda_events['fwd_return_5d'],
                      nvda_events['ceiling_score'])],
            hovertemplate='%{text}<extra></extra>',
            name='NVDA Earnings'
        ))

        fig3.add_hline(y=2, line_dash="dash", line_color="yellow",
                      annotation_text="Narrative Ceiling Threshold")

        fig3.update_layout(
            title='NVDA Earnings History: Ceiling Score Over Time (Green=Up, Red=Fade)',
            template='plotly_dark',
            height=500,
            yaxis_title='Ceiling Score',
            xaxis_title='Earnings Date'
        )

        chart_path = CHARTS_DIR / "nvda_ceiling_timeline.html"
        fig3.write_html(str(chart_path))
        print(f"  ✅ Chart saved: {chart_path}")

except Exception as e:
    print(f"  ❌ Chart 3 failed: {e}")

# ═══════════════════════════════════════════════════════
# PHASE 10: SAVE ALL OUTPUTS
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PHASE 10: Saving outputs...")
print("-" * 40)

# Save events CSV
events_output = analysis_df.sort_values(['ceiling_score', 'date'],
                                         ascending=[False, False])
events_output.to_csv(OUTPUT_DIR / "all_events.csv", index=False)
print(f"  ✅ Events saved: {OUTPUT_DIR / 'all_events.csv'}")

# Save condition power
if len(condition_power_df) > 0:
    condition_power_df.to_csv(OUTPUT_DIR / "condition_power.csv", index=False)
    print(f"  ✅ Condition power saved: {OUTPUT_DIR / 'condition_power.csv'}")

# Save NVDA deep dive
if len(nvda_events) > 0:
    nvda_events.to_csv(OUTPUT_DIR / "nvda_deep_dive.csv", index=False)
    print(f"  ✅ NVDA deep dive saved: {OUTPUT_DIR / 'nvda_deep_dive.csv'}")

# Save summary stats
summary_path = OUTPUT_DIR / "summary_stats.txt"
with open(summary_path, 'w') as f:
    f.write("BEAT & SELL PROBABILITY STUDY — SUMMARY\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Study Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"Universe: {len(all_data)} stocks\n")
    f.write(f"Period: {START_DATE} to {END_DATE}\n")
    f.write(f"Total gap-up events: {len(analysis_df)}\n")
    f.write(f"Gap-up threshold: >{GAP_UP_THRESHOLD*100:.0f}%\n\n")

    f.write("REGIME DISTRIBUTION:\n")
    for regime, count in regime_counts.items():
        f.write(f"  {regime}: {count}\n")

    f.write(f"\nKEY FINDING:\n")
    if len(ceiling_group) > 0 and len(clean_group) > 0:
        clean_fade = clean_group['day_of_fade'].mean()
        ceil_fade = ceiling_group['day_of_fade'].mean()
        f.write(f"  Clean (score 0-1) day fade rate: {clean_fade*100:.1f}%\n")
        f.write(f"  Ceiling (score 2+) day fade rate: {ceil_fade*100:.1f}%\n")
        f.write(f"  Fade rate LIFT: {(ceil_fade - clean_fade)*100:+.1f} ppts\n")
        f.write(f"  Clean 5d mean return: {clean_group['fwd_return_5d'].mean()*100:+.2f}%\n")
        f.write(f"  Ceiling 5d mean return: {ceiling_group['fwd_return_5d'].mean()*100:+.2f}%\n")

print(f"  ✅ Summary saved: {summary_path}")

# ═══════════════════════════════════════════════════════
# PHASE 11: README
# ═══════════════════════════════════════════════════════

readme_path = STUDY_DIR / "README.md"
with open(readme_path, 'w') as f:
    f.write("# Beat & Sell Probability Study — Narrative Ceiling Fade\n\n")
    f.write("## Hypothesis\n")
    f.write("When mega-cap stocks beat earnings into structural distribution "
            "(no new highs, weak RS, beat compression, pre-earnings front-running), "
            "the probability of a post-earnings FADE is significantly elevated.\n\n")
    f.write("## Methodology\n")
    f.write("- Universe: 25 mega-cap stocks (2020-2026)\n")
    f.write("- Earnings detected via overnight gap >2% + volume spike\n")
    f.write("- 5 structural conditions scored (0-5 composite)\n")
    f.write("- Forward returns measured: day-of, +1d, +3d, +5d, +10d\n\n")
    f.write("## Conditions Measured\n")
    f.write("1. Days since ATH > 60 (distribution)\n")
    f.write("2. 60-day range compressed <15% (stuck in box)\n")
    f.write("3. RS vs SPY trailing 20d <= 0 (weak relative strength)\n")
    f.write("4. Pre-earnings 5d drift > 3% (front-running)\n")
    f.write("5. 3+ consecutive gap-up earnings (beat fatigue)\n\n")
    f.write("## Trading Application\n")
    f.write("- Ceiling Score 0-1: Standard post-earnings behavior\n")
    f.write("- Ceiling Score 2: Elevated fade risk — reduce size or wait\n")
    f.write("- Ceiling Score 3+: NARRATIVE CEILING — strong fade probability\n")
    f.write("  Consider: stand aside, fade the gap, or wait for post-earnings dip to buy\n\n")
    f.write("## War Room Integration\n")
    f.write("If confirmed, add as § 9F BEAT ABSORPTION FILTER to the War Room prompt.\n")
    f.write("Modifies position management on earnings plays, not conviction scoring.\n")

print(f"  ✅ README saved: {readme_path}")

# ═══════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("🔬 STUDY COMPLETE — BEAT & SELL PROBABILITY")
print("=" * 70)
print(f"""
KEY NUMBERS:
  Total gap-up earnings events: {len(analysis_df)}
  Ceiling events (score 2+): {len(ceiling_group)}
  Extreme ceiling events (score 3+): {len(extreme_group)}

WHAT TO LOOK FOR IN RESULTS:
  1. Does the day-of fade rate INCREASE as ceiling score rises?
  2. Is there a statistically meaningful difference between clean and ceiling?
  3. Which individual conditions have the most predictive power?
  4. Does NVDA specifically show this pattern?

IF THE STUDY CONFIRMS THE EDGE:
  → New War Room section: § 9F BEAT ABSORPTION FILTER
  → New setup: [NARRATIVE CEILING FADE SHORT]
  → Modifies earnings play sizing when ceiling score >= 2
  → Does NOT change catalyst scoring — changes position management

OUTPUTS:
  📊 {CHARTS_DIR / 'ceiling_score_vs_outcomes.html'}
  📊 {CHARTS_DIR / 'condition_power.html'}
  📊 {CHARTS_DIR / 'nvda_ceiling_timeline.html'}
  📋 {OUTPUT_DIR / 'all_events.csv'}
  📋 {OUTPUT_DIR / 'nvda_deep_dive.csv'}
  📋 {OUTPUT_DIR / 'condition_power.csv'}
  📝 {OUTPUT_DIR / 'summary_stats.txt'}
  📖 {readme_path}
""")

print("Study execution complete. 🚀")

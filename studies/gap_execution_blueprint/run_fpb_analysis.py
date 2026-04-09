## ═══════════════════════════════════════════════════════════════
## STUDY: First Pullback to EMA Cloud (FPB) — Extension
## ═══════════════════════════════════════════════════════════════
## Compares the original 40% ATR follow-through entry against a
## "First Pullback to EMA Cloud" entry. For each gap event that
## had follow-through, we find the first bar AFTER that follow-
## through where price pulls back into the 10/21 EMA cloud, then
## measure win rate, MAE, MFE, and R:R from THAT entry.
## ═══════════════════════════════════════════════════════════════

import sys, os, time
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\indicators')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')

from shared.data_router import DataRouter
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

## ═══════════════════════════════════════════════════════════════
## CONFIGURATION
## ═══════════════════════════════════════════════════════════════

OUTPUT_DIR = r'C:\QuantLab\Data_Lab\studies\gap_execution_blueprint\outputs'
RESULTS_CSV = os.path.join(OUTPUT_DIR, 'execution_blueprint_events.csv')
GAP_CACHE_CSV = os.path.join(OUTPUT_DIR, 'gap_events_cache.csv')

SESSION_OPEN_ET  = "09:30"
SESSION_CLOSE_ET = "16:00"

EMA_FAST = 10
EMA_SLOW = 21
MIN_BARS_FOR_EMA = 4   # Skip first 4 bars (20 min) — EMAs haven't repriced to gap yet

FOLLOW_THROUGH_ATR_PCT = 0.40
CHUNK_DAYS = 120

## ═══════════════════════════════════════════════════════════════
## STEP 1: LOAD EXISTING STUDY RESULTS
## ═══════════════════════════════════════════════════════════════

t0 = time.time()
print("=" * 70)
print("STEP 1: Loading existing study results")
print("=" * 70)

results_df = pd.read_csv(RESULTS_CSV)
print(f"Loaded {len(results_df)} events from execution_blueprint_events.csv")
print(f"Columns: {results_df.columns.tolist()}")

# Also load gap_events_cache for ATR / follow_through_level (has all 12K events)
gap_cache_df = pd.read_csv(GAP_CACHE_CSV)
# Build a lookup: (ticker, date) → {atr, follow_through_level, open_price}
gap_lookup = {}
for _, row in gap_cache_df.iterrows():
    key = (row['ticker'], row['date'])
    gap_lookup[key] = {
        'atr': row['atr'],
        'follow_through_level': row['follow_through_level'],
        'open_price': row['open_price'],
        'prev_close': row['prev_close']
    }

# Filter to only included-in-analysis events (have follow-through)
analysis_df = results_df[results_df['included_in_analysis'] == True].copy()
print(f"Events included in analysis (have FT): {len(analysis_df)}")
print(f"Unique tickers: {analysis_df['ticker'].nunique()}")
print(f"Step 1 took {time.time()-t0:.1f}s")

## ═══════════════════════════════════════════════════════════════
## STEP 2: RE-PULL 5-MIN BARS PER-TICKER (CHUNKED CACHING)
## ═══════════════════════════════════════════════════════════════

t1 = time.time()
print("\n" + "=" * 70)
print("STEP 2: Building per-ticker intraday cache (no fallback)")
print("=" * 70)

events_by_ticker = defaultdict(list)
for _, event in analysis_df.iterrows():
    events_by_ticker[event['ticker']].append(pd.Timestamp(event['date']))

ticker_cache = {}
total_calls = 0
total_ok = 0
total_fail = 0

for i, (ticker, event_dates) in enumerate(sorted(events_by_ticker.items())):
    if (i + 1) % 25 == 0 or (i + 1) == len(events_by_ticker):
        elapsed = time.time() - t1
        print(f"  Ticker {i+1}/{len(events_by_ticker)} | {total_ok} chunks ok, {total_fail} fail | {elapsed:.0f}s")

    min_dt = min(event_dates) - timedelta(days=1)
    max_dt = max(event_dates) + timedelta(days=1)

    chunks = []
    cursor = min_dt
    while cursor <= max_dt:
        chunk_end = cursor + timedelta(days=CHUNK_DAYS)
        if chunk_end > max_dt:
            chunk_end = max_dt
        chunks.append((cursor.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        cursor = chunk_end + timedelta(days=1)

    ticker_frames = []
    for start_str, end_str in chunks:
        total_calls += 1
        try:
            intraday = DataRouter.get_price_data(
                ticker, start_str, end_date=end_str,
                timeframe='5min', fallback=False
            )
            if intraday is None or len(intraday) == 0:
                total_fail += 1
                continue
            intraday = intraday.sort_index()
            if isinstance(intraday.index, pd.DatetimeIndex) and intraday.index.tz is not None:
                intraday.index = intraday.index.tz_convert('US/Eastern')
            ticker_frames.append(intraday)
            total_ok += 1
        except Exception:
            total_fail += 1
            continue

    if ticker_frames:
        combined = pd.concat(ticker_frames).sort_index()
        combined = combined[~combined.index.duplicated(keep='last')]
        ticker_cache[ticker] = combined

elapsed = time.time() - t1
print(f"\nTicker cache built: {len(ticker_cache)} tickers, {total_calls} API calls "
      f"({total_ok} ok, {total_fail} fail) in {elapsed:.0f}s\n")

## ═══════════════════════════════════════════════════════════════
## STEPS 3-6: PROCESS EACH EVENT
## ═══════════════════════════════════════════════════════════════

t2 = time.time()
print("=" * 70)
print("STEPS 3-6: Computing EMA cloud + FPB for each event")
print("=" * 70)

fpb_results = []
skipped_events = []
no_data_count = 0
total_events_count = len(analysis_df)

for i, (idx, event) in enumerate(analysis_df.iterrows()):
    if (i + 1) % 500 == 0 or (i + 1) == total_events_count:
        print(f"  Processing {i+1}/{total_events_count}... ({len([r for r in fpb_results if r.get('fpb_occurred')])} FPBs found)")

    try:
        ticker = event['ticker']
        event_date = pd.Timestamp(event['date'])

        # ── Get session bars from cache ──
        ticker_intraday = ticker_cache.get(ticker)
        if ticker_intraday is None:
            skipped_events.append((ticker, str(event_date), 'no_ticker_cache'))
            no_data_count += 1
            continue

        day_bars = ticker_intraday[ticker_intraday.index.date == event_date.date()]
        if day_bars is None or len(day_bars) < 20:
            skipped_events.append((ticker, str(event_date), 'insufficient_bars'))
            no_data_count += 1
            continue

        session = day_bars.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
        if len(session) < 15:
            skipped_events.append((ticker, str(event_date), 'short_session'))
            no_data_count += 1
            continue

        # ── Step 3: Calculate EMAs ──
        session = session.copy()
        session['ema10'] = session['Close'].ewm(span=EMA_FAST, adjust=False).mean()
        session['ema21'] = session['Close'].ewm(span=EMA_SLOW, adjust=False).mean()
        session['cloud_upper'] = session[['ema10', 'ema21']].max(axis=1)
        session['cloud_lower'] = session[['ema10', 'ema21']].min(axis=1)

        # ── Step 4: Re-detect follow-through bar ──
        gap_key = (ticker, event['date'])
        gap_info = gap_lookup.get(gap_key)
        if gap_info is None:
            gap_info = gap_lookup.get((ticker, str(event_date)))
        if gap_info is None:
            skipped_events.append((ticker, str(event_date), 'no_gap_info'))
            no_data_count += 1
            continue

        ft_level = gap_info['follow_through_level']
        atr = gap_info['atr']
        open_price = gap_info['open_price']

        ft_bar_idx = None
        for j in range(len(session)):
            if session.iloc[j]['Close'] >= ft_level:
                ft_bar_idx = j
                break

        if ft_bar_idx is None:
            skipped_events.append((ticker, str(event_date), 'ft_bar_not_found'))
            no_data_count += 1
            continue

        original_entry_price = session.iloc[ft_bar_idx]['Close']
        original_entry_time = session.index[ft_bar_idx]

        # Original metrics (from existing study)
        orig_eod_return = event['eod_return']
        orig_mae = event['mae_pct']
        orig_mfe = event['mfe_pct']
        eod_close = session.iloc[-1]['Close']

        # ── Step 5: Find First Pullback to EMA Cloud ──
        scan_start = max(ft_bar_idx + 1, MIN_BARS_FOR_EMA)

        fpb_bar_idx = None
        fpb_entry_price = None

        for j in range(scan_start, len(session)):
            bar_low = session.iloc[j]['Low']
            cloud_upper_val = session.iloc[j]['cloud_upper']

            # FPB: bar LOW touches or dips into the cloud from above
            if bar_low <= cloud_upper_val:
                fpb_bar_idx = j
                fpb_entry_price = session.iloc[j]['Close']
                break

        fpb_occurred = fpb_bar_idx is not None

        # ── Step 6: Calculate FPB Metrics ──
        if fpb_occurred and fpb_entry_price is not None and fpb_entry_price > 0:
            fpb_entry_time = session.index[fpb_bar_idx]
            post_fpb = session.iloc[fpb_bar_idx:]

            if len(post_fpb) > 0:
                fpb_mae_price = post_fpb['Low'].min()
                fpb_mae_pct = (fpb_mae_price - fpb_entry_price) / fpb_entry_price
            else:
                fpb_mae_pct = 0.0

            if len(post_fpb) > 0:
                fpb_mfe_price = post_fpb['High'].max()
                fpb_mfe_pct = (fpb_mfe_price - fpb_entry_price) / fpb_entry_price
            else:
                fpb_mfe_pct = 0.0

            fpb_eod_return = (eod_close - fpb_entry_price) / fpb_entry_price

            if fpb_mae_pct != 0:
                fpb_rr = fpb_mfe_pct / abs(fpb_mae_pct)
            else:
                fpb_rr = float('inf') if fpb_mfe_pct > 0 else 0.0

            if orig_mae != 0:
                orig_rr = orig_mfe / abs(orig_mae)
            else:
                orig_rr = float('inf') if orig_mfe > 0 else 0.0

            price_improvement = (original_entry_price - fpb_entry_price) / original_entry_price
            bars_until_fpb = fpb_bar_idx - ft_bar_idx
            fpb_time_minutes = (fpb_entry_time - session.index[0]).total_seconds() / 60

        else:
            fpb_entry_time = None
            fpb_mae_pct = None
            fpb_mfe_pct = None
            fpb_eod_return = None
            fpb_rr = None
            orig_rr = orig_mfe / abs(orig_mae) if orig_mae != 0 else (float('inf') if orig_mfe > 0 else 0.0)
            price_improvement = None
            bars_until_fpb = None
            fpb_time_minutes = None

        fpb_results.append({
            'ticker': ticker,
            'date': event_date,
            'gap_pct': event['gap_pct'],
            'open_price': open_price,
            'atr': atr,
            'candle_color': event['candle_color'],

            # Original entry metrics
            'orig_entry_price': original_entry_price,
            'orig_entry_time': original_entry_time,
            'orig_eod_return': orig_eod_return,
            'orig_mae_pct': orig_mae,
            'orig_mfe_pct': orig_mfe,
            'orig_rr': orig_rr,

            # FPB metrics
            'fpb_occurred': fpb_occurred,
            'fpb_bar_idx': fpb_bar_idx,
            'fpb_entry_price': fpb_entry_price,
            'fpb_entry_time': fpb_entry_time,
            'fpb_eod_return': fpb_eod_return,
            'fpb_mae_pct': fpb_mae_pct,
            'fpb_mfe_pct': fpb_mfe_pct,
            'fpb_rr': fpb_rr,
            'price_improvement': price_improvement,
            'bars_until_fpb': bars_until_fpb,
            'fpb_time_minutes': fpb_time_minutes,
        })

    except Exception as e:
        skipped_events.append((ticker if 'ticker' in dir() else '?', str(event_date) if 'event_date' in dir() else '?', str(e)))
        no_data_count += 1
        continue

print(f"\nEvent processing done in {time.time()-t2:.1f}s")
print(f"Total processed: {len(fpb_results)} | Skipped: {no_data_count}")

## ═══════════════════════════════════════════════════════════════
## STEP 7: BUILD COMPARISON ANALYSIS
## ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 7: COMPARISON — 40% ATR Entry vs First Pullback to EMA Cloud")
print("=" * 70)

df = pd.DataFrame(fpb_results)
fpb_valid = df[df['fpb_occurred'] == True].copy()

# Cap infinite R:R values for stats
for col in ['orig_rr', 'fpb_rr']:
    df[col] = df[col].replace([np.inf, -np.inf], np.nan)
    fpb_valid[col] = fpb_valid[col].replace([np.inf, -np.inf], np.nan)

# ── Main comparison table ──
total_events = len(df)
fpb_count = len(fpb_valid)
fpb_pct = fpb_count / total_events * 100 if total_events > 0 else 0

orig_wr = (df['orig_eod_return'] > 0).mean() * 100
fpb_wr = (fpb_valid['fpb_eod_return'] > 0).mean() * 100 if fpb_count > 0 else 0

orig_avg_ret = df['orig_eod_return'].mean() * 100
fpb_avg_ret = fpb_valid['fpb_eod_return'].mean() * 100 if fpb_count > 0 else 0

orig_med_mae = df['orig_mae_pct'].median() * 100
fpb_med_mae = fpb_valid['fpb_mae_pct'].median() * 100 if fpb_count > 0 else 0

orig_med_mfe = df['orig_mfe_pct'].median() * 100
fpb_med_mfe = fpb_valid['fpb_mfe_pct'].median() * 100 if fpb_count > 0 else 0

orig_med_rr = df['orig_rr'].dropna().median()
fpb_med_rr = fpb_valid['fpb_rr'].dropna().median() if fpb_count > 0 else 0

avg_bars = fpb_valid['bars_until_fpb'].mean() if fpb_count > 0 else 0
avg_price_imp = fpb_valid['price_improvement'].mean() * 100 if fpb_count > 0 else 0

comparison = f"""
{'Metric':<30s} | {'40% ATR Entry':>15s} | {'FPB Entry':>15s}
{'-'*30}-+-{'-'*15}-+-{'-'*15}
{'Total Events':<30s} | {total_events:>15d} | {fpb_count:>15d}
{'Win Rate':<30s} | {orig_wr:>14.1f}% | {fpb_wr:>14.1f}%
{'Avg Return (EOD)':<30s} | {orig_avg_ret:>+14.2f}% | {fpb_avg_ret:>+14.2f}%
{'Median MAE %':<30s} | {orig_med_mae:>+14.2f}% | {fpb_med_mae:>+14.2f}%
{'Median MFE %':<30s} | {orig_med_mfe:>+14.2f}% | {fpb_med_mfe:>+14.2f}%
{'Median R:R (MFE/MAE)':<30s} | {orig_med_rr:>15.2f} | {fpb_med_rr:>15.2f}
{'% Events where FPB occurs':<30s} | {'N/A':>15s} | {fpb_pct:>14.1f}%
{'Avg bars until FPB':<30s} | {'N/A':>15s} | {avg_bars:>15.1f}
{'Avg price improvement':<30s} | {'N/A':>15s} | {avg_price_imp:>+14.2f}%
"""
print(comparison)

# ── Breakdown by gap size ──
print("=" * 70)
print("FPB Win Rate by Gap Size Bucket")
print("=" * 70)

for low, high, label in [(0.02, 0.05, '2-5%'), (0.05, 0.08, '5-8%'),
                           (0.08, 0.12, '8-12%'), (0.12, 1.0, '12%+')]:
    bucket = fpb_valid[(fpb_valid['gap_pct'] >= low) & (fpb_valid['gap_pct'] < high)]
    n = len(bucket)
    if n < 5:
        print(f"  Gap {label}: n={n} (too few)")
        continue
    wr = (bucket['fpb_eod_return'] > 0).mean() * 100
    avg_ret = bucket['fpb_eod_return'].mean() * 100
    med_mae = bucket['fpb_mae_pct'].median() * 100
    med_rr = bucket['fpb_rr'].dropna().median()
    orig_wr_b = (bucket['orig_eod_return'] > 0).mean() * 100
    print(f"  Gap {label} (n={n}): FPB WR={wr:.1f}% (orig {orig_wr_b:.1f}%) | "
          f"Avg Ret={avg_ret:+.2f}% | Med MAE={med_mae:+.2f}% | Med R:R={med_rr:.2f}")

# ── Breakdown by candle class ──
print("\n" + "=" * 70)
print("FPB Win Rate by Opening Candle Color")
print("=" * 70)

for color in ['BULLISH', 'NEUTRAL']:
    group = fpb_valid[fpb_valid['candle_color'] == color]
    n = len(group)
    if n < 5:
        continue
    wr = (group['fpb_eod_return'] > 0).mean() * 100
    avg_ret = group['fpb_eod_return'].mean() * 100
    med_rr = group['fpb_rr'].dropna().median()
    orig_wr_g = (group['orig_eod_return'] > 0).mean() * 100
    print(f"  {color} (n={n}): FPB WR={wr:.1f}% (orig {orig_wr_g:.1f}%) | "
          f"Avg Ret={avg_ret:+.2f}% | Med R:R={med_rr:.2f}")

# ── Breakdown by time of FPB ──
print("\n" + "=" * 70)
print("FPB Win Rate by Time of Pullback (CT = ET - 60 min)")
print("=" * 70)

# Pre-11 AM CT = pre-12 PM ET = first 150 min from open
pre_11 = fpb_valid[fpb_valid['fpb_time_minutes'] <= 150]
post_11 = fpb_valid[fpb_valid['fpb_time_minutes'] > 150]

for label, group in [('Pre-11 AM CT (first 2.5 hrs)', pre_11),
                      ('Post-11 AM CT', post_11)]:
    n = len(group)
    if n < 5:
        print(f"  {label}: n={n} (too few)")
        continue
    wr = (group['fpb_eod_return'] > 0).mean() * 100
    avg_ret = group['fpb_eod_return'].mean() * 100
    med_rr = group['fpb_rr'].dropna().median()
    print(f"  {label} (n={n}): FPB WR={wr:.1f}% | Avg Ret={avg_ret:+.2f}% | Med R:R={med_rr:.2f}")

## ═══════════════════════════════════════════════════════════════
## STEP 8: PRICE IMPROVEMENT ANALYSIS
## ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 8: Price Improvement Analysis")
print("=" * 70)

if fpb_count > 0:
    pi = fpb_valid['price_improvement'].dropna()
    cheaper_pct = (pi > 0).mean() * 100
    more_expensive_pct = (pi < 0).mean() * 100

    print(f"  Events with valid FPB: {fpb_count}")
    print(f"  Median price improvement:  {pi.median()*100:+.2f}%")
    print(f"  Mean price improvement:    {pi.mean()*100:+.2f}%")
    print(f"  FPB entry is CHEAPER than 40% entry: {cheaper_pct:.1f}% of events")
    print(f"  FPB entry is MORE EXPENSIVE:         {more_expensive_pct:.1f}% of events")
    print(f"  (Positive = you're getting in lower / better price)")
else:
    print("  No FPB events found.")

## ═══════════════════════════════════════════════════════════════
## STEP 9: SAVE RESULTS
## ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 9: Saving results")
print("=" * 70)

csv_path = os.path.join(OUTPUT_DIR, 'fpb_analysis_results.csv')
df.to_csv(csv_path, index=False)
print(f"  Saved: {csv_path}")

summary_path = os.path.join(OUTPUT_DIR, 'fpb_summary_stats.txt')
with open(summary_path, 'w') as f:
    f.write("=" * 70 + "\n")
    f.write("FPB (First Pullback to EMA Cloud) vs 40% ATR Entry — Summary\n")
    f.write("=" * 70 + "\n\n")
    f.write(comparison)
    f.write("\n\n")

    f.write("Gap Size Breakdown:\n")
    for low, high, label in [(0.02, 0.05, '2-5%'), (0.05, 0.08, '5-8%'),
                               (0.08, 0.12, '8-12%'), (0.12, 1.0, '12%+')]:
        bucket = fpb_valid[(fpb_valid['gap_pct'] >= low) & (fpb_valid['gap_pct'] < high)]
        n = len(bucket)
        if n < 5:
            f.write(f"  Gap {label}: n={n} (too few)\n")
            continue
        wr = (bucket['fpb_eod_return'] > 0).mean() * 100
        avg_ret = bucket['fpb_eod_return'].mean() * 100
        orig_wr_b = (bucket['orig_eod_return'] > 0).mean() * 100
        med_rr = bucket['fpb_rr'].dropna().median()
        f.write(f"  Gap {label} (n={n}): FPB WR={wr:.1f}% (orig {orig_wr_b:.1f}%) | "
                f"Avg Ret={avg_ret:+.2f}% | Med R:R={med_rr:.2f}\n")

    f.write("\nCandle Color Breakdown:\n")
    for color in ['BULLISH', 'NEUTRAL']:
        group = fpb_valid[fpb_valid['candle_color'] == color]
        n = len(group)
        if n < 5:
            continue
        wr = (group['fpb_eod_return'] > 0).mean() * 100
        orig_wr_g = (group['orig_eod_return'] > 0).mean() * 100
        med_rr = group['fpb_rr'].dropna().median()
        f.write(f"  {color} (n={n}): FPB WR={wr:.1f}% (orig {orig_wr_g:.1f}%) | Med R:R={med_rr:.2f}\n")

    f.write("\nTime of FPB Breakdown (CT):\n")
    for label, group in [('Pre-11 AM CT', pre_11), ('Post-11 AM CT', post_11)]:
        n = len(group)
        if n < 5:
            continue
        wr = (group['fpb_eod_return'] > 0).mean() * 100
        med_rr = group['fpb_rr'].dropna().median()
        f.write(f"  {label} (n={n}): FPB WR={wr:.1f}% | Med R:R={med_rr:.2f}\n")

    f.write(f"\nPrice Improvement:\n")
    if fpb_count > 0:
        pi = fpb_valid['price_improvement'].dropna()
        f.write(f"  Median: {pi.median()*100:+.2f}% | Mean: {pi.mean()*100:+.2f}%\n")
        f.write(f"  FPB cheaper: {(pi > 0).mean()*100:.1f}% | More expensive: {(pi < 0).mean()*100:.1f}%\n")

    f.write(f"\nSkipped events: {no_data_count}\n")

print(f"  Saved: {summary_path}")

## ═══════════════════════════════════════════════════════════════
## FINAL SUMMARY
## ═══════════════════════════════════════════════════════════════

total_time = time.time() - t0
print("\n" + "=" * 70)
print("=== FINAL SUMMARY ===")
print("=" * 70)

print(f"  1. Total events analyzed: {total_events}")
print(f"  2. Events with valid FPB: {fpb_count} ({fpb_pct:.1f}% of total)")
print(f"  3. Win rates:  40% ATR = {orig_wr:.1f}%  |  FPB = {fpb_wr:.1f}%")
print(f"  4. Median R:R: 40% ATR = {orig_med_rr:.2f} |  FPB = {fpb_med_rr:.2f}")

# Verdict
if fpb_count >= 50:
    wr_diff = fpb_wr - orig_wr
    rr_diff = fpb_med_rr - orig_med_rr

    if wr_diff > 3 and rr_diff > 0.1:
        verdict = "BETTER"
    elif wr_diff < -3 and rr_diff < -0.1:
        verdict = "WORSE"
    elif abs(wr_diff) <= 3 and abs(rr_diff) <= 0.1:
        verdict = "SIMILAR"
    elif rr_diff > 0.2:
        verdict = "BETTER (R:R driven)"
    elif rr_diff < -0.2:
        verdict = "WORSE (R:R driven)"
    elif wr_diff > 3:
        verdict = "BETTER (WR driven)"
    elif wr_diff < -3:
        verdict = "WORSE (WR driven)"
    else:
        verdict = "SIMILAR (mixed signals)"
else:
    verdict = "INSUFFICIENT DATA"

print(f"\n  >>> The verdict: FPB is {verdict} than the 40% threshold entry based on R:R and win rate")
print(f"\n  Skipped events: {no_data_count}")
print(f"  Total runtime: {total_time:.0f}s ({total_time/60:.1f} min)")
print(f"\n  Output files:")
print(f"    {csv_path}")
print(f"    {summary_path}")

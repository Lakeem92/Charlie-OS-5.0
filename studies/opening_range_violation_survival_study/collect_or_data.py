"""
Opening Range Violation Survival Study — Data Collection
=========================================================
Loads gap event universe from existing candle-strength study cache,
pulls intraday 5-min data per ticker, computes opening-range violation
metrics for all 4 gap paths.

Reuses: all_events_with_cs.csv (n=11,733) from opening_candle_strength
Adds:   bar-1 extremes, OR violation tracking, depth/timing, post-violation MFE/MAE
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from shared.data_router import DataRouter

# ─── Configuration ───────────────────────────────────────────────
STUDY_DIR = Path(r'C:\QuantLab\Data_Lab\studies\opening_range_violation_survival_study')
RUN_ID = 'run_20260309'
OUTPUT_DIR = STUDY_DIR / 'outputs' / RUN_ID
CACHE_FILE = OUTPUT_DIR / 'or_master_events.csv'

# Sibling cache from opening_candle_strength study
EVENTS_CS_PATH = Path(r'C:\QuantLab\Data_Lab\studies\opening_candle_strength\outputs\all_events_with_cs.csv')

# Matching existing gap-study parameters exactly
ATR_PERIOD = 14
FT_ATR_MULT = 0.40
CHUNK_DAYS = 120
SESSION_OPEN_ET = "09:30"
SESSION_CLOSE_ET = "16:00"

# Follow-through tiers (ATR-normalized close from open)
FT_TIER1_ATR = 0.70
FT_TIER2_ATR = 1.00


# ─── Helper Functions ────────────────────────────────────────────

def violation_depth_bucket(depth_atr):
    if depth_atr <= 0:
        return 'no_violation'
    if depth_atr <= 0.10:
        return '0-0.10 ATR'
    if depth_atr <= 0.25:
        return '0.10-0.25 ATR'
    if depth_atr <= 0.50:
        return '0.25-0.50 ATR'
    return '0.50+ ATR'


def timing_bucket_abs(minutes):
    """Absolute timing bucket from session open."""
    if pd.isna(minutes):
        return 'unknown'
    if minutes <= 5:
        return 'at_open'
    if minutes <= 30:
        return 'first_30min'
    if minutes <= 60:
        return '30min_to_1hr'
    if minutes <= 120:
        return '1hr_to_2hr'
    if minutes <= 240:
        return '2hr_to_4hr'
    if minutes <= 360:
        return 'after_4hr'
    return 'last_30min'


def timing_bucket_rel_ft(viol_minutes, ft_minutes, ft_fired):
    """Classify violation timing relative to FT trigger."""
    if pd.isna(viol_minutes):
        return 'no_violation'
    if not ft_fired or pd.isna(ft_minutes):
        # FT never fired; bucket by absolute time
        if viol_minutes <= 30:
            return 'pre_ft_early'
        if viol_minutes <= 120:
            return 'pre_ft_mid'
        return 'pre_ft_late'
    diff = viol_minutes - ft_minutes
    if diff < 0:
        return 'pre_ft'
    if diff <= 15:
        return '0_to_15min_after_ft'
    if diff <= 30:
        return '15_to_30min_after_ft'
    if diff <= 120:
        return '30min_plus_after_ft'
    return 'late_after_ft'


# ─── Phase 1: Load & Classify Events ────────────────────────────

def load_and_classify_events():
    """Load events from candle-strength study cache and classify into 4 paths."""
    print("=" * 70)
    print("PHASE 1: Loading event universe from all_events_with_cs.csv")
    print("=" * 70)

    events = pd.read_csv(EVENTS_CS_PATH)
    print(f"  Loaded {len(events)} events")

    # Parse trade dates — handles both "2024-01-24 05:00:00+00:00" and "2024-02-02" formats
    raw_dates = pd.to_datetime(events['date'], utc=True, format='mixed')
    events['trade_date'] = raw_dates.dt.tz_convert('US/Eastern').dt.date

    # ── Path classification (matches existing gap-study definitions)
    conditions = [
        (events['direction'] == 'GAP_UP') & (~events['candle_tier'].isin(['BEARISH', 'MAX_BEARISH'])),
        (events['direction'] == 'GAP_DN') & (~events['candle_tier'].isin(['BULLISH', 'MAX_BULLISH'])),
        (events['direction'] == 'GAP_UP') & (events['candle_tier'].isin(['BEARISH', 'MAX_BEARISH'])),
        (events['direction'] == 'GAP_DN') & (events['candle_tier'].isin(['BULLISH', 'MAX_BULLISH'])),
    ]
    choices = [
        'gapup_continuation_long',
        'gapdown_continuation_short',
        'gapup_fade_short',
        'gapdown_bounce_long',
    ]
    events['path_type'] = np.select(conditions, choices, default='unknown')

    events['setup_direction'] = events['path_type'].map({
        'gapup_continuation_long': 'LONG',
        'gapdown_continuation_short': 'SHORT',
        'gapup_fade_short': 'SHORT',
        'gapdown_bounce_long': 'LONG',
    })

    # ── Path-appropriate FT (continuation → std_ft, fade/bounce → reverse_ft)
    is_cont = events['path_type'].isin(['gapup_continuation_long', 'gapdown_continuation_short'])

    events['path_ft_fired'] = np.where(is_cont, events['std_ft_fired'], events['reverse_ft_fired'])
    events['path_ft_minutes'] = np.where(is_cont, events['std_ft_minutes'], events['reverse_ft_minutes'])
    events['path_reverse_ft_fired'] = np.where(is_cont, events['reverse_ft_fired'], events['std_ft_fired'])
    events['path_reverse_ft_minutes'] = np.where(is_cont, events['reverse_ft_minutes'], events['std_ft_minutes'])

    # FT trigger reference price
    events['ft_trigger_ref_price'] = np.where(
        events['setup_direction'] == 'LONG',
        events['open_price'] + events['atr'] * FT_ATR_MULT,
        events['open_price'] - events['atr'] * FT_ATR_MULT,
    )

    # ── Pre-compute outcome metrics from existing columns (no intraday needed)
    events['close_from_open_abs'] = np.where(
        events['setup_direction'] == 'LONG',
        events['eod_close'] - events['open_price'],
        events['open_price'] - events['eod_close'],
    )
    events['close_from_open_pct'] = events['close_from_open_abs'] / events['open_price']
    events['close_from_open_atr'] = events['close_from_open_abs'] / events['atr']
    events['achieved_0p70_atr'] = events['close_from_open_atr'] >= FT_TIER1_ATR
    events['achieved_1p00_atr'] = events['close_from_open_atr'] >= FT_TIER2_ATR

    # Destination & adverse timing from existing HoD/LoD
    events['destination_minutes'] = np.where(
        events['setup_direction'] == 'LONG',
        events['hod_minutes'],
        events['lod_minutes'],
    )
    events['adverse_peak_minutes'] = np.where(
        events['setup_direction'] == 'LONG',
        events['lod_minutes'],
        events['hod_minutes'],
    )
    events['destination_timing_bucket'] = events['destination_minutes'].apply(timing_bucket_abs)
    events['adverse_timing_bucket'] = events['adverse_peak_minutes'].apply(timing_bucket_abs)

    print("\n  Path distribution:")
    for p in choices:
        n = len(events[events['path_type'] == p])
        print(f"    {p}: {n:,}")

    return events


# ─── Phase 2: Intraday Pull & OR Metric Computation ─────────────

def pull_intraday_for_ticker(ticker, event_dates):
    """Pull 5-min intraday data spanning all event dates for a ticker."""
    dates_sorted = sorted(event_dates)
    min_dt = dates_sorted[0] - timedelta(days=1)
    max_dt = dates_sorted[-1] + timedelta(days=1)

    chunks = []
    cursor = min_dt
    while cursor <= max_dt:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), max_dt)
        chunks.append((cursor.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        cursor = chunk_end + timedelta(days=1)

    all_frames = []
    for start_str, end_str in chunks:
        try:
            df = DataRouter.get_price_data(
                ticker, start_str, end_date=end_str,
                timeframe='5min', fallback=False
            )
            if df is not None and len(df) > 0:
                df = df.sort_index()
                if isinstance(df.index, pd.DatetimeIndex):
                    if df.index.tz is not None:
                        df.index = df.index.tz_convert('US/Eastern')
                    else:
                        df.index = df.index.tz_localize('UTC').tz_convert('US/Eastern')
                all_frames.append(df)
        except Exception:
            pass  # skip failed chunks quietly

    if all_frames:
        combined = pd.concat(all_frames).sort_index()
        combined = combined[~combined.index.duplicated(keep='first')]
        return combined
    return None


def compute_or_metrics_for_event(event, session):
    """Compute opening-range violation metrics for a single event."""
    if session is None or len(session) < 2:
        return None

    bar1 = session.iloc[0]
    open_price = event['open_price']
    atr = event['atr']
    setup_dir = event['setup_direction']

    if atr <= 0 or open_price <= 0:
        return None

    result = {}

    # ── Bar-1 (opening 5-min) extremes
    result['open_5m_high'] = bar1['High']
    result['open_5m_low'] = bar1['Low']
    result['open_5m_close'] = bar1['Close']
    result['open_5m_range'] = bar1['High'] - bar1['Low']
    result['open_5m_range_atr'] = result['open_5m_range'] / atr

    # ── Relevant OR level (adverse extreme)
    or_level = bar1['Low'] if setup_dir == 'LONG' else bar1['High']
    result['relevant_or_level'] = or_level

    # ── Post-bar1 violation detection
    post_bar1 = session.iloc[1:]

    if len(post_bar1) == 0:
        # Edge case: only 1 bar in session
        result['or_violated'] = False
        result['first_or_violation_minutes'] = np.nan
        result['max_violation_depth_abs'] = 0.0
        result['max_violation_depth_pct'] = 0.0
        result['max_violation_depth_atr'] = 0.0
        result['violation_depth_bucket'] = 'no_violation'
        result['violation_timing_abs_bucket'] = 'no_violation'
        result['violation_timing_rel_bucket'] = 'no_violation'
        for pfx in ['mfe_after_violation', 'mae_after_violation']:
            for sfx in ['_abs', '_pct', '_atr']:
                result[f'{pfx}{sfx}'] = np.nan
        return result

    if setup_dir == 'LONG':
        violation_mask = post_bar1['Low'] < or_level
    else:
        violation_mask = post_bar1['High'] > or_level

    violated = violation_mask.any()
    result['or_violated'] = violated

    if violated:
        violations = post_bar1[violation_mask]
        first_viol_time = violations.index[0]
        viol_minutes = (first_viol_time - session.index[0]).total_seconds() / 60
        result['first_or_violation_minutes'] = viol_minutes

        # Max depth
        if setup_dir == 'LONG':
            worst_price = post_bar1['Low'].min()
            max_depth = max(or_level - worst_price, 0)
        else:
            worst_price = post_bar1['High'].max()
            max_depth = max(worst_price - or_level, 0)

        result['max_violation_depth_abs'] = max_depth
        result['max_violation_depth_pct'] = max_depth / open_price
        result['max_violation_depth_atr'] = max_depth / atr

        result['violation_depth_bucket'] = violation_depth_bucket(result['max_violation_depth_atr'])
        result['violation_timing_abs_bucket'] = timing_bucket_abs(viol_minutes)
        result['violation_timing_rel_bucket'] = timing_bucket_rel_ft(
            viol_minutes, event['path_ft_minutes'], event['path_ft_fired']
        )

        # MFE / MAE after first violation
        post_viol = post_bar1.loc[first_viol_time:]
        if len(post_viol) > 0:
            if setup_dir == 'LONG':
                mfe = max(post_viol['High'].max() - open_price, 0)
                mae = max(open_price - post_viol['Low'].min(), 0)
            else:
                mfe = max(open_price - post_viol['Low'].min(), 0)
                mae = max(post_viol['High'].max() - open_price, 0)
            result['mfe_after_violation_abs'] = mfe
            result['mfe_after_violation_pct'] = mfe / open_price
            result['mfe_after_violation_atr'] = mfe / atr
            result['mae_after_violation_abs'] = mae
            result['mae_after_violation_pct'] = mae / open_price
            result['mae_after_violation_atr'] = mae / atr
        else:
            for pfx in ['mfe_after_violation', 'mae_after_violation']:
                for sfx in ['_abs', '_pct', '_atr']:
                    result[f'{pfx}{sfx}'] = np.nan
    else:
        result['first_or_violation_minutes'] = np.nan
        result['max_violation_depth_abs'] = 0.0
        result['max_violation_depth_pct'] = 0.0
        result['max_violation_depth_atr'] = 0.0
        result['violation_depth_bucket'] = 'no_violation'
        result['violation_timing_abs_bucket'] = 'no_violation'
        result['violation_timing_rel_bucket'] = 'no_violation'
        for pfx in ['mfe_after_violation', 'mae_after_violation']:
            for sfx in ['_abs', '_pct', '_atr']:
                result[f'{pfx}{sfx}'] = np.nan

    return result


# ─── Main Pipeline ───────────────────────────────────────────────

def run_collection():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists():
        print(f"\nCache exists at {CACHE_FILE} — loading and skipping collection.")
        return pd.read_csv(CACHE_FILE)

    events = load_and_classify_events()

    print("\n" + "=" * 70)
    print("PHASE 2: Pulling intraday data & computing OR metrics")
    print("=" * 70)

    ticker_groups = events.groupby('ticker')
    tickers = sorted(ticker_groups.groups.keys())
    print(f"  Processing {len(tickers)} tickers...\n")

    enriched_rows = []
    skipped = 0
    processed = 0
    intraday_failures = 0
    t0 = time.time()

    for i, ticker in enumerate(tickers, 1):
        grp = ticker_groups.get_group(ticker)
        trade_dates = grp['trade_date'].tolist()

        intraday = pull_intraday_for_ticker(ticker, trade_dates)

        if intraday is None or len(intraday) == 0:
            skipped += len(grp)
            intraday_failures += 1
            continue

        for _, event in grp.iterrows():
            td = event['trade_date']
            day_data = intraday[intraday.index.date == td]
            if len(day_data) == 0:
                skipped += 1
                continue

            session = day_data.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
            if len(session) < 2:
                skipped += 1
                continue

            or_metrics = compute_or_metrics_for_event(event, session)
            if or_metrics is None:
                skipped += 1
                continue

            # Combine original event fields + new OR metrics into one row
            row = event.to_dict()
            row.update(or_metrics)
            enriched_rows.append(row)
            processed += 1

        elapsed = time.time() - t0
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = len(events) - processed - skipped
        eta = remaining / rate / 60 if rate > 0 else 0

        if i % 10 == 0 or i == len(tickers):
            print(
                f"  [{i:>3}/{len(tickers)}] {ticker:<6} | "
                f"done={processed:,}  skip={skipped:,}  | "
                f"{elapsed:.0f}s  ETA={eta:.1f}min"
            )

    print(f"\n  COMPLETE: {processed:,} events enriched, {skipped:,} skipped")
    print(f"  Intraday failures: {intraday_failures} tickers")
    print(f"  Total time: {(time.time() - t0) / 60:.1f} minutes")

    enriched = pd.DataFrame(enriched_rows)
    enriched.to_csv(CACHE_FILE, index=False)
    print(f"  Saved to {CACHE_FILE}")

    return enriched


if __name__ == '__main__':
    run_collection()

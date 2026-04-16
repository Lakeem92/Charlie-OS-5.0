# -*- coding: utf-8 -*-
"""
===================================================================
STUDY: Gap Fade - Contrary Candle Analysis
===============================================================
THE question: "When a stock gaps up 2%+ but opens with a BEARISH
candle, does the fade play work? And when a stock gaps down 2%+
but opens with a BULLISH candle, does the bounce play work?"

This study captures the events that gap_execution_blueprint
(long) and gap_down_execution_blueprint (short) deliberately
EXCLUDE - the contrary candle cases. The indicator currently
shows "CONTRARY CANDLE - NO STUDY EDGE" for these. This study
will either confirm that label or replace it with data-backed
fade/bounce guidance.

EVENT TYPES:
  1. GAP-UP FADE:   Gap >= 2%, first 5-min candle BEARISH
                     Fade FT = 5-min close <= Open - (ATR14 x 0.40)
  2. GAP-DOWN BOUNCE: Gap <= -2%, first 5-min candle BULLISH
                     Bounce FT = 5-min close >= Open + (ATR14 x 0.40)

SPEED: Reuses existing daily gap caches from sibling studies
when available, cutting ~15 min off the daily scan phase.
===============================================================
"""

import sys, os, time
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')

from shared.data_router import DataRouter
from shared.watchlist import get_watchlist
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ===============================================================
# CONFIGURATION
# ===============================================================

UNIVERSE = get_watchlist()
START_DATE = '2024-01-01'
END_DATE   = '2026-03-07'
GAP_THRESHOLD       = 0.02        # 2% minimum gap (absolute)
ATR_PERIOD          = 14
FT_ATR_PCT          = 0.40        # 40% of ATR = follow-through threshold
BODY_RATIO_THRESHOLD = 0.40       # body > 40% of range = directional candle
CHUNK_DAYS          = 120         # ~6 months per API chunk (under 10K bar limit)

SESSION_OPEN_ET  = "09:30"
SESSION_CLOSE_ET = "16:00"

OUTPUT_DIR = r'C:\QuantLab\Data_Lab\studies\gap_fade_contrary_candle\outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sibling study caches (reuse if available)
GAPUP_CACHE   = r'C:\QuantLab\Data_Lab\studies\gap_execution_blueprint\outputs\gap_events_cache.csv'
GAPDN_CACHE   = r'C:\QuantLab\Data_Lab\studies\gap_down_execution_blueprint\outputs\gap_down_events_cache.csv'
LOCAL_CACHE    = os.path.join(OUTPUT_DIR, 'gap_fade_events_cache.csv')


# ===============================================================
# OPENING CANDLE CLASSIFICATION
# ===============================================================

def classify_candle(row):
    """Classify a candle the way you read the chart."""
    o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
    rng = h - l
    if rng == 0:
        return 'NEUTRAL'
    body = abs(c - o)
    body_pct = body / rng
    if body_pct <= BODY_RATIO_THRESHOLD:
        return 'NEUTRAL'
    elif c > o:
        return 'BULLISH'
    else:
        return 'BEARISH'


# ===============================================================
# STEP 1: FIND ALL GAP EVENTS + COMPUTE ATR
# ===============================================================
# Try to reuse sibling study caches. If not, scan from scratch.
# ===============================================================

t0 = time.time()
print("=" * 70)
print("GAP FADE - CONTRARY CANDLE STUDY")
print(f"Universe: {len(UNIVERSE)} tickers | {START_DATE} to {END_DATE}")
print("=" * 70)

if os.path.exists(LOCAL_CACHE):
    print("\nSTEP 1: Loading from local cache")
    gap_df = pd.read_csv(LOCAL_CACHE)
    print(f"Loaded {len(gap_df)} events ({gap_df['direction'].value_counts().to_dict()})")
    print(f"Step 1: {time.time()-t0:.1f}s (cached)")

elif os.path.exists(GAPUP_CACHE) and os.path.exists(GAPDN_CACHE):
    print("\nSTEP 1: Reusing sibling study caches (fast path)")

    gapup_df = pd.read_csv(GAPUP_CACHE)
    gapdn_df = pd.read_csv(GAPDN_CACHE)

    # Normalize gap-up cache
    up_events = []
    for _, r in gapup_df.iterrows():
        up_events.append({
            'ticker': r['ticker'],
            'date': r['date'],
            'open_price': r['open_price'],
            'prev_close': r['prev_close'],
            'gap_pct': r['gap_pct'],
            'atr': r['atr'],
            'direction': 'GAP_UP',
            'ft_level_fade': r['open_price'] - (r['atr'] * FT_ATR_PCT),
            'ft_level_go': r.get('follow_through_level', r['open_price'] + (r['atr'] * FT_ATR_PCT)),
        })

    # Normalize gap-down cache
    dn_events = []
    for _, r in gapdn_df.iterrows():
        dn_events.append({
            'ticker': r['ticker'],
            'date': r['date'],
            'open_price': r['open_price'],
            'prev_close': r['prev_close'],
            'gap_pct': r['gap_pct'],
            'atr': r['atr'],
            'direction': 'GAP_DN',
            'ft_level_fade': r['open_price'] + (r['atr'] * FT_ATR_PCT),  # bounce = upside FT
            'ft_level_go': r.get('follow_through_level', r['open_price'] - (r['atr'] * FT_ATR_PCT)),
        })

    gap_df = pd.DataFrame(up_events + dn_events)
    print(f"Loaded {len(gapup_df)} gap-ups + {len(gapdn_df)} gap-downs = {len(gap_df)} total events")
    gap_df.to_csv(LOCAL_CACHE, index=False)
    print(f"Saved local cache: {LOCAL_CACHE}")
    print(f"Step 1: {time.time()-t0:.1f}s")

else:
    print("\nSTEP 1: Scanning daily data for gap events (no sibling caches found)")
    all_gap_events = []
    api_ok = 0
    api_fail = 0

    for i, ticker in enumerate(UNIVERSE):
        if (i + 1) % 25 == 0 or (i + 1) == len(UNIVERSE):
            print(f"  Scanning {i+1}/{len(UNIVERSE)} tickers... ({len(all_gap_events)} events)")
        try:
            daily = DataRouter.get_price_data(ticker, START_DATE, end_date=END_DATE, timeframe='daily')
            if daily is None or len(daily) < ATR_PERIOD + 5:
                api_fail += 1
                continue
            api_ok += 1
            daily = daily.sort_index()

            # ATR calculation
            high_s = daily['High']
            low_s = daily['Low']
            close_s = daily['Close']
            prev_close = close_s.shift(1)
            tr = pd.concat([
                (high_s - low_s),
                (high_s - prev_close).abs(),
                (low_s - prev_close).abs()
            ], axis=1).max(axis=1)
            daily['atr'] = tr.rolling(ATR_PERIOD).mean()
            daily['prev_close'] = prev_close
            daily['gap_pct'] = (daily['Open'] - prev_close) / prev_close

            for idx_dt, row in daily.iterrows():
                if pd.isna(row['gap_pct']) or pd.isna(row['atr']) or row['atr'] <= 0:
                    continue

                abs_gap = abs(row['gap_pct'])
                if abs_gap < GAP_THRESHOLD:
                    continue

                direction = 'GAP_UP' if row['gap_pct'] >= GAP_THRESHOLD else 'GAP_DN'

                # Fade FT level: opposite direction of gap
                if direction == 'GAP_UP':
                    ft_fade = row['Open'] - (row['atr'] * FT_ATR_PCT)
                    ft_go = row['Open'] + (row['atr'] * FT_ATR_PCT)
                else:
                    ft_fade = row['Open'] + (row['atr'] * FT_ATR_PCT)
                    ft_go = row['Open'] - (row['atr'] * FT_ATR_PCT)

                all_gap_events.append({
                    'ticker': ticker,
                    'date': pd.Timestamp(idx_dt).strftime('%Y-%m-%d'),
                    'open_price': row['Open'],
                    'prev_close': row['prev_close'],
                    'gap_pct': round(row['gap_pct'], 6),
                    'atr': round(row['atr'], 4),
                    'direction': direction,
                    'ft_level_fade': round(ft_fade, 4),
                    'ft_level_go': round(ft_go, 4),
                })
        except Exception:
            api_fail += 1
            continue

    gap_df = pd.DataFrame(all_gap_events)
    if len(gap_df) == 0:
        print("\n!  No gap events found. Check watchlist/data.")
        sys.exit(0)

    print(f"\nFound {len(gap_df)} gap events across {gap_df['ticker'].nunique()} tickers")
    print(f"  Gap-ups: {(gap_df['direction']=='GAP_UP').sum()} | Gap-downs: {(gap_df['direction']=='GAP_DN').sum()}")
    print(f"  API ok: {api_ok} | fail: {api_fail}")
    gap_df.to_csv(LOCAL_CACHE, index=False)
    print(f"Saved: {LOCAL_CACHE}")
    print(f"Step 1: {time.time()-t0:.1f}s")


# ===============================================================
# STEP 2: BUILD PER-TICKER INTRADAY CACHE
# ===============================================================

t1 = time.time()
print("\n" + "=" * 70)
print("STEP 2: Building per-ticker 5-min intraday cache")
print("=" * 70)

events_by_ticker = defaultdict(list)
for _, event in gap_df.iterrows():
    events_by_ticker[event['ticker']].append(event)

ticker_cache = {}
total_calls = 0
total_ok = 0
total_fail = 0

for i, (ticker, events) in enumerate(sorted(events_by_ticker.items())):
    if (i + 1) % 25 == 0 or (i + 1) == len(events_by_ticker):
        elapsed = time.time() - t1
        print(f"  Ticker {i+1}/{len(events_by_ticker)} | "
              f"{total_ok} chunks ok, {total_fail} fail | {elapsed:.0f}s")

    event_dates = [pd.Timestamp(e['date']).tz_localize(None) for e in events]
    min_dt = min(event_dates) - timedelta(days=1)
    max_dt = max(event_dates) + timedelta(days=1)

    # 120-day chunk windows
    chunks = []
    cursor = min_dt
    while cursor <= max_dt:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), max_dt)
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
      f"({total_ok} ok, {total_fail} fail) in {elapsed:.0f}s")


# ===============================================================
# STEP 3: CLASSIFY + MEASURE (CONTRARY CANDLE EVENTS ONLY)
# ===============================================================
# Gap-ups: keep ONLY BEARISH first candle -> check DOWNSIDE FT
# Gap-downs: keep ONLY BULLISH first candle -> check UPSIDE FT
# ===============================================================

t2 = time.time()
print("\n" + "=" * 70)
print("STEP 3: Classifying contrary candles + measuring fade/bounce metrics")
print("=" * 70)

results = []
no_data = 0
wrong_candle = 0
no_ft = 0
total = len(gap_df)

for i, (idx, event) in enumerate(gap_df.iterrows()):
    if (i + 1) % 2000 == 0 or (i + 1) == total:
        print(f"  Processing {i+1}/{total}... "
              f"({len(results)} contrary-confirmed, {wrong_candle} wrong candle, {no_ft} no FT)")

    try:
        ticker = event['ticker']
        event_date = pd.Timestamp(event['date'])
        direction = event['direction']

        ticker_intraday = ticker_cache.get(ticker)
        if ticker_intraday is None:
            no_data += 1
            continue

        day_bars = ticker_intraday[ticker_intraday.index.date == event_date.date()]
        if day_bars is None or len(day_bars) < 10:
            no_data += 1
            continue

        session = day_bars.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
        if len(session) < 10:
            no_data += 1
            continue

        # --- FIRST CANDLE CLASSIFICATION ---
        bar1 = session.iloc[0]
        candle_color = classify_candle(bar1)

        # FILTER: We ONLY want contrary candles
        # Gap-up -> need BEARISH candle; Gap-down -> need BULLISH candle
        if direction == 'GAP_UP' and candle_color != 'BEARISH':
            wrong_candle += 1
            continue
        if direction == 'GAP_DN' and candle_color != 'BULLISH':
            wrong_candle += 1
            continue

        # --- FOLLOW-THROUGH CHECK (FADE DIRECTION) ---
        ft_level = event['ft_level_fade']
        session_open_time = session.index[0]
        open_price = event['open_price']
        atr = event['atr']

        ft_bar_idx = None
        if direction == 'GAP_UP':
            # Fade FT: first 5-min close <= Open - (ATR x 0.40)
            for j in range(len(session)):
                if session.iloc[j]['Close'] <= ft_level:
                    ft_bar_idx = j
                    break
        else:
            # Bounce FT: first 5-min close >= Open + (ATR x 0.40)
            for j in range(len(session)):
                if session.iloc[j]['Close'] >= ft_level:
                    ft_bar_idx = j
                    break

        has_ft = ft_bar_idx is not None

        # --- ENTRY + METRICS (if FT confirmed) ---
        entry_price = session.iloc[ft_bar_idx]['Close'] if has_ft else None
        entry_time = session.index[ft_bar_idx] if has_ft else None
        eod_close = session.iloc[-1]['Close']

        # Session extremes
        session_high = session['High'].max()
        session_low = session['Low'].min()
        session_high_idx = session['High'].idxmax()
        session_low_idx = session['Low'].idxmin()
        hod_minutes = (session_high_idx - session_open_time).total_seconds() / 60.0
        lod_minutes = (session_low_idx - session_open_time).total_seconds() / 60.0

        # Gap bucket
        abs_gap = abs(event['gap_pct'])
        if abs_gap >= 0.12:
            gap_bucket = '12%+'
        elif abs_gap >= 0.08:
            gap_bucket = '8-12%'
        elif abs_gap >= 0.05:
            gap_bucket = '5-8%'
        else:
            gap_bucket = '2-5%'

        # Base row (always recorded, even without FT)
        row_data = {
            'ticker': ticker,
            'date': event_date.strftime('%Y-%m-%d'),
            'direction': direction,
            'gap_pct': event['gap_pct'],
            'abs_gap_pct': abs_gap,
            'gap_bucket': gap_bucket,
            'atr': atr,
            'open_price': open_price,
            'prev_close': event['prev_close'],
            'candle_color': candle_color,
            'ft_level': ft_level,
            'has_ft': has_ft,
            'session_high': session_high,
            'session_low': session_low,
            'eod_close': eod_close,
            'hod_minutes_from_open': round(hod_minutes, 1),
            'lod_minutes_from_open': round(lod_minutes, 1),
        }

        if not has_ft:
            # Still record: EOD return from OPEN (no entry, but shows gap behavior)
            if direction == 'GAP_UP':
                row_data['eod_return_from_open'] = (open_price - eod_close) / open_price  # short from open
            else:
                row_data['eod_return_from_open'] = (eod_close - open_price) / open_price  # long from open
            no_ft += 1
            results.append(row_data)
            continue

        # --- POST-ENTRY METRICS (FT confirmed) ---
        ft_minutes = (entry_time - session_open_time).total_seconds() / 60.0
        post_entry = session.iloc[ft_bar_idx:]
        after_entry = session.iloc[ft_bar_idx + 1:] if ft_bar_idx + 1 < len(session) else pd.DataFrame()

        if direction == 'GAP_UP':
            # SHORT perspective (fading a gap-up)
            eod_return = (entry_price - eod_close) / entry_price
            mae_price = post_entry['High'].max()
            mfe_price = post_entry['Low'].min()
            mae_pct = (mae_price - entry_price) / entry_price    # positive = bad (bounce against short)
            mfe_pct = (entry_price - mfe_price) / entry_price    # positive = good (drop in favor)

            # Price goes above entry after FT?
            adverse_after_ft = False
            if len(after_entry) > 0:
                adverse_after_ft = bool((after_entry['High'] > entry_price).any())

            # Bounce depth before LoD (worst case before continuation)
            bounce_depth_before_dest = 0.0
            if len(after_entry) > 0:
                post_low_idx = after_entry['Low'].idxmin()
                bars_before_dest = after_entry[after_entry.index <= post_low_idx]
                if len(bars_before_dest) > 0:
                    worst = bars_before_dest['High'].max()
                    bounce_depth_before_dest = (worst - entry_price) / entry_price

            # Did it close above open? (full reversal against fade)
            close_above_open = eod_close > open_price

        else:
            # LONG perspective (bouncing a gap-down)
            eod_return = (eod_close - entry_price) / entry_price
            mae_price = post_entry['Low'].min()
            mfe_price = post_entry['High'].max()
            mae_pct = (entry_price - mae_price) / entry_price    # positive = bad (dip against long)
            mfe_pct = (mfe_price - entry_price) / entry_price    # positive = good (rise in favor)

            adverse_after_ft = False
            if len(after_entry) > 0:
                adverse_after_ft = bool((after_entry['Low'] < entry_price).any())

            bounce_depth_before_dest = 0.0
            if len(after_entry) > 0:
                post_high_idx = after_entry['High'].idxmax()
                bars_before_dest = after_entry[after_entry.index <= post_high_idx]
                if len(bars_before_dest) > 0:
                    worst = bars_before_dest['Low'].min()
                    bounce_depth_before_dest = (entry_price - worst) / entry_price

            close_above_open = eod_close > open_price

        # Forward returns from entry bar
        fwd_returns = {}
        for label, bars in [('15min', 3), ('30min', 6), ('1hr', 12), ('2hr', 24)]:
            target = ft_bar_idx + bars
            if target < len(session):
                if direction == 'GAP_UP':
                    fwd_returns[f'fwd_{label}'] = (entry_price - session.iloc[target]['Close']) / entry_price
                else:
                    fwd_returns[f'fwd_{label}'] = (session.iloc[target]['Close'] - entry_price) / entry_price
            else:
                fwd_returns[f'fwd_{label}'] = eod_return

        row_data.update({
            'entry_price': round(entry_price, 4),
            'entry_time': str(entry_time),
            'ft_minutes_from_open': round(ft_minutes, 1),
            'eod_return': round(eod_return, 6),
            'eod_return_from_open': round(
                ((open_price - eod_close) / open_price) if direction == 'GAP_UP'
                else ((eod_close - open_price) / open_price), 6),
            'mae_pct': round(mae_pct, 6),
            'mfe_pct': round(mfe_pct, 6),
            'adverse_after_ft': adverse_after_ft,
            'bounce_depth_before_dest': round(bounce_depth_before_dest, 6),
            'close_above_open': close_above_open,
            **{k: round(v, 6) for k, v in fwd_returns.items()},
        })

        results.append(row_data)

    except Exception:
        no_data += 1
        continue

results_df = pd.DataFrame(results)

elapsed3 = time.time() - t2
print(f"\nStep 3 complete in {elapsed3:.0f}s")
print(f"  Total events scanned:        {total}")
print(f"  Wrong candle (non-contrary):  {wrong_candle}")
print(f"  No intraday data:            {no_data}")
print(f"  Contrary candle, no FT:      {no_ft}")
print(f"  Contrary candle, FT confirmed: {len(results_df[results_df['has_ft']==True])}")
print(f"  Total recorded:              {len(results_df)}")

# Save all
results_path = os.path.join(OUTPUT_DIR, 'results_analysis.csv')
results_df.to_csv(results_path, index=False)
print(f"Saved: {results_path}")

if len(results_df) == 0:
    print("\n!  No contrary candle events found.")
    sys.exit(0)


# ===============================================================
# STEP 4: ANALYSIS - THE ANSWERS
# ===============================================================

print("\n" + "=" * 70)
print("STEP 4: CONTRARY CANDLE STUDY RESULTS")
print("=" * 70)

output_lines = []


def prt(line=""):
    print(line)
    output_lines.append(line)


# Split into the two event types
fade_all = results_df[results_df['direction'] == 'GAP_UP'].copy()
bounce_all = results_df[results_df['direction'] == 'GAP_DN'].copy()
fade_ft = fade_all[fade_all['has_ft'] == True].copy()
bounce_ft = bounce_all[bounce_all['has_ft'] == True].copy()

prt(f"\n{'='*70}")
prt("POPULATION SUMMARY")
prt(f"{'='*70}")
prt(f"  Gap-ups with BEARISH first candle:    {len(fade_all)}")
prt(f"    -> Fade FT confirmed:                {len(fade_ft)} ({len(fade_ft)/max(len(fade_all),1)*100:.1f}%)")
prt(f"    -> No FT (gap held):                 {len(fade_all)-len(fade_ft)}")
prt(f"  Gap-downs with BULLISH first candle:   {len(bounce_all)}")
prt(f"    -> Bounce FT confirmed:              {len(bounce_ft)} ({len(bounce_ft)/max(len(bounce_all),1)*100:.1f}%)")
prt(f"    -> No FT (gap held):                 {len(bounce_all)-len(bounce_ft)}")
prt(f"  Unique tickers:                       {results_df['ticker'].nunique()}")
prt(f"  Date range:                           {START_DATE} to {END_DATE}")


# ===============================================================
# FINDING 0: Does the contrary candle ITSELF predict the fade?
# (Even without FT - just having a bearish bar 1 on a gap-up)
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 0: CONTRARY CANDLE AS RAW SIGNAL (no FT filter)")
prt("  Does a bearish bar-1 on a gap-up mean the gap will fade by EOD?")
prt("  Does a bullish bar-1 on a gap-down mean it bounces by EOD?")
prt(f"{'='*70}")

for label, sub in [("GAP-UP + BEARISH BAR-1 (fade signal)", fade_all),
                    ("GAP-DN + BULLISH BAR-1 (bounce signal)", bounce_all)]:
    if len(sub) == 0:
        prt(f"\n  {label}: No events")
        continue
    eod_open = sub['eod_return_from_open'].dropna()
    n = len(eod_open)
    wr = (eod_open > 0).mean() * 100 if n > 0 else 0
    avg = eod_open.mean() * 100 if n > 0 else 0
    med = eod_open.median() * 100 if n > 0 else 0
    ft_rate = sub['has_ft'].mean() * 100

    prt(f"\n  {label} (n={n})")
    prt(f"    EOD Win Rate (from open):  {wr:.1f}%")
    prt(f"    Avg EOD Return (from open): {avg:+.2f}%")
    prt(f"    Median EOD Return:          {med:+.2f}%")
    prt(f"    FT Confirmation Rate:       {ft_rate:.1f}%")


# ===============================================================
# FINDING 1: FT-CONFIRMED FADE/BOUNCE WIN RATES
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 1: FT-CONFIRMED CONTRARY TRADES")
prt("  Gap-up fades: SHORT entry at Fade-FT bar close")
prt("  Gap-down bounces: LONG entry at Bounce-FT bar close")
prt(f"{'='*70}")

for label, sub in [("GAP-UP FADE (short)", fade_ft),
                    ("GAP-DN BOUNCE (long)", bounce_ft)]:
    if len(sub) == 0:
        prt(f"\n  {label}: No events")
        continue
    eod = sub['eod_return'].dropna()
    n = len(eod)
    wr = (eod > 0).mean() * 100
    avg = eod.mean() * 100
    med = eod.median() * 100
    winners = eod[eod > 0]
    losers = eod[eod <= 0]
    avg_w = winners.mean() * 100 if len(winners) > 0 else 0
    avg_l = losers.mean() * 100 if len(losers) > 0 else 0
    rr = abs(avg_w / avg_l) if avg_l != 0 else 0

    prt(f"\n  {label} (n={n})")
    prt(f"    EOD Win Rate:       {wr:.1f}%")
    prt(f"    Avg EOD Return:     {avg:+.2f}%")
    prt(f"    Median EOD Return:  {med:+.2f}%")
    prt(f"    Avg Winner:         {avg_w:+.2f}%")
    prt(f"    Avg Loser:          {avg_l:+.2f}%")
    prt(f"    R:R Ratio:          {rr:.2f}:1")

    for col, lbl in [('fwd_15min', '15min'), ('fwd_30min', '30min'),
                      ('fwd_1hr', '1hr'), ('fwd_2hr', '2hr')]:
        if col in sub.columns:
            vals = sub[col].dropna()
            if len(vals) > 0:
                prt(f"    {lbl:>6s} fwd: {vals.mean()*100:+.2f}% | WR: {(vals>0).mean()*100:.1f}%")


# ===============================================================
# FINDING 2: GAP SIZE BUCKETS
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 2: BY GAP SIZE BUCKET (FT-confirmed only)")
prt(f"{'='*70}")

buckets = [
    ('2-5%',   0.02, 0.05),
    ('5-8%',   0.05, 0.08),
    ('8-12%',  0.08, 0.12),
    ('12%+',   0.12, 1.00),
]

for type_label, sub in [("GAP-UP FADE (short)", fade_ft),
                         ("GAP-DN BOUNCE (long)", bounce_ft)]:
    prt(f"\n  -- {type_label} --")
    prt(f"  {'Bucket':<8s} {'n':>5s} {'WR':>7s} {'AvgRet':>9s} {'MedMAE':>9s} {'MedMFE':>9s} {'FTmin':>7s}")
    prt(f"  {'-'*8} {'-'*5} {'-'*7} {'-'*9} {'-'*9} {'-'*9} {'-'*7}")

    for blabel, lo, hi in buckets:
        bucket = sub[(sub['abs_gap_pct'] >= lo) & (sub['abs_gap_pct'] < hi)]
        if len(bucket) < 3:
            prt(f"  {blabel:<8s} {len(bucket):>5d}   (too few)")
            continue
        eod = bucket['eod_return'].dropna()
        wr = (eod > 0).mean() * 100
        avg_ret = eod.mean() * 100
        med_mae = bucket['mae_pct'].dropna().median() * 100 if 'mae_pct' in bucket.columns else 0
        med_mfe = bucket['mfe_pct'].dropna().median() * 100 if 'mfe_pct' in bucket.columns else 0
        med_ft = bucket['ft_minutes_from_open'].dropna().median() if 'ft_minutes_from_open' in bucket.columns else 0
        prt(f"  {blabel:<8s} {len(bucket):>5d} {wr:>6.1f}% {avg_ret:>+8.2f}% "
            f" {med_mae:>+8.2f}%  {med_mfe:>+7.2f}% {med_ft:>6.0f}m")


# ===============================================================
# FINDING 3: TIMING - LoD / HoD
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 3: TIMING (LoD / HoD) - FT-confirmed")
prt(f"{'='*70}")

for type_label, sub, dest_label, dest_col, worst_label, worst_col in [
    ("GAP-UP FADE", fade_ft, "LoD", "lod_minutes_from_open", "HoD", "hod_minutes_from_open"),
    ("GAP-DN BOUNCE", bounce_ft, "HoD", "hod_minutes_from_open", "LoD", "lod_minutes_from_open"),
]:
    if len(sub) == 0:
        continue
    dest = sub[dest_col].dropna()
    worst = sub[worst_col].dropna()

    prt(f"\n  -- {type_label} (n={len(sub)}) --")
    prt(f"  {dest_label} (destination - where money is):")
    prt(f"    Median: {dest.median():.0f} min ({int(dest.median())//60}h {int(dest.median())%60}m)")
    prt(f"    In first 30 min:  {(dest<=30).mean()*100:.1f}%")
    prt(f"    In first 60 min:  {(dest<=60).mean()*100:.1f}%")
    prt(f"    In first 2 hrs:   {(dest<=120).mean()*100:.1f}%")
    prt(f"    In last hour:     {(dest>=330).mean()*100:.1f}%")

    prt(f"  {worst_label} (adverse - worst case):")
    prt(f"    Median: {worst.median():.0f} min ({int(worst.median())//60}h {int(worst.median())%60}m)")
    prt(f"    In first 30 min:  {(worst<=30).mean()*100:.1f}%")
    prt(f"    In last hour:     {(worst>=330).mean()*100:.1f}%")


# ===============================================================
# FINDING 4: MAE / MFE PROFILE
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 4: P&L PROFILE (FT-confirmed)")
prt(f"{'='*70}")

for type_label, sub in [("GAP-UP FADE (short from FT)", fade_ft),
                         ("GAP-DN BOUNCE (long from FT)", bounce_ft)]:
    if len(sub) == 0 or 'mae_pct' not in sub.columns:
        continue
    mae = sub['mae_pct'].dropna()
    mfe = sub['mfe_pct'].dropna()

    prt(f"\n  -- {type_label} (n={len(sub)}) --")
    prt(f"  MAE (worst move against you):")
    prt(f"    Median: {mae.median()*100:+.2f}%")
    prt(f"    Mean:   {mae.mean()*100:+.2f}%")
    prt(f"    Worst 10%: {mae.quantile(0.90)*100:+.2f}%")
    prt(f"  MFE (best move in your favor):")
    prt(f"    Median: {mfe.median()*100:+.2f}%")
    prt(f"    Mean:   {mfe.mean()*100:+.2f}%")
    prt(f"    Best 10%: {mfe.quantile(0.90)*100:+.2f}%")

    adv = sub['adverse_after_ft'].mean() * 100
    prt(f"  Price goes adverse after FT: {adv:.1f}%")

    if 'bounce_depth_before_dest' in sub.columns:
        bd = sub['bounce_depth_before_dest'].dropna()
        prt(f"  Adverse excursion before destination:")
        prt(f"    Median: {bd.median()*100:+.2f}%")
        prt(f"    90th pct: {bd.quantile(0.90)*100:+.2f}%")

    # Pullback zones (for potential indicator integration)
    prt(f"  MAE Percentile Zones (for indicator pullback labels):")
    for pctile, plabel in [(0.25, '25th'), (0.50, 'Median'), (0.75, '75th'), (0.90, '90th')]:
        prt(f"    {plabel:>8s}: {mae.quantile(pctile)*100:+.2f}%")


# ===============================================================
# FINDING 5: GAP-UP FADE - Does it close below the open?
# (Key question: does the gap actually FILL or just pull back?)
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 5: GAP FILL ANALYSIS")
prt(f"{'='*70}")

if len(fade_ft) > 0:
    # For gap-up fades: did price close below the OPEN?
    close_below_open = (fade_ft['close_above_open'] == False).mean() * 100
    prt(f"\n  GAP-UP FADES -> Close BELOW open (gap reversal): {close_below_open:.1f}%")

    # Did price reach prev_close? (full gap fill)
    if 'prev_close' in fade_ft.columns and 'session_low' in fade_ft.columns:
        full_fill = (fade_ft['session_low'] <= fade_ft['prev_close']).mean() * 100
        prt(f"  GAP-UP FADES -> Session low reaches prev close (full fill): {full_fill:.1f}%")

if len(bounce_ft) > 0:
    close_above_open_bounce = bounce_ft['close_above_open'].mean() * 100
    prt(f"\n  GAP-DN BOUNCES -> Close ABOVE open (gap reversal): {close_above_open_bounce:.1f}%")

    if 'prev_close' in bounce_ft.columns and 'session_high' in bounce_ft.columns:
        full_fill = (bounce_ft['session_high'] >= bounce_ft['prev_close']).mean() * 100
        prt(f"  GAP-DN BOUNCES -> Session high reaches prev close (full fill): {full_fill:.1f}%")


# ===============================================================
# FINDING 6: FT TIMING - How fast does the fade confirm?
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 6: FT CONFIRMATION TIMING")
prt(f"{'='*70}")

for type_label, sub in [("GAP-UP FADE", fade_ft), ("GAP-DN BOUNCE", bounce_ft)]:
    if len(sub) == 0 or 'ft_minutes_from_open' not in sub.columns:
        continue
    ft = sub['ft_minutes_from_open'].dropna()
    prt(f"\n  {type_label} (n={len(sub)}):")
    prt(f"    Median FT time: {ft.median():.0f} min from open")
    prt(f"    FT in first 5 min:  {(ft<=5).mean()*100:.1f}%")
    prt(f"    FT in first 15 min: {(ft<=15).mean()*100:.1f}%")
    prt(f"    FT in first 30 min: {(ft<=30).mean()*100:.1f}%")
    prt(f"    FT in first 60 min: {(ft<=60).mean()*100:.1f}%")
    prt(f"    FT after 2 hours:   {(ft>=120).mean()*100:.1f}%")


# ===============================================================
# FINDING 7: COMPARISON TO CONTINUATION STUDIES
# (How do contrary candle fades compare to the go-with studies?)
# ===============================================================

prt(f"\n{'='*70}")
prt("FINDING 7: CONTRARY vs CONTINUATION COMPARISON")
prt("  (Reference: gap_execution_blueprint long WR ~51%, gap_down short WR ~45%)")
prt(f"{'='*70}")

if len(fade_ft) > 0:
    fade_wr = (fade_ft['eod_return'].dropna() > 0).mean() * 100
    prt(f"\n  Gap-up FADE (bearish bar-1, short): {fade_wr:.1f}% WR  (n={len(fade_ft)})")
    prt(f"  Gap-up CONTINUATION (bull/neut bar-1, long): ~51% WR  (n=1,865 from sibling study)")
    prt(f"  -> Difference: {fade_wr - 51:+.1f}pp")

if len(bounce_ft) > 0:
    bounce_wr = (bounce_ft['eod_return'].dropna() > 0).mean() * 100
    prt(f"\n  Gap-down BOUNCE (bullish bar-1, long): {bounce_wr:.1f}% WR  (n={len(bounce_ft)})")
    prt(f"  Gap-down CONTINUATION (bear/neut bar-1, short): ~45% WR  (n=1,861 from sibling study)")
    prt(f"  -> Difference: {bounce_wr - 45:+.1f}pp")


# ===============================================================
# SAVE SUMMARY
# ===============================================================

summary_path = os.path.join(OUTPUT_DIR, 'summary_stats.txt')
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))
prt(f"\nSaved: {summary_path}")


# ===============================================================
# FINAL SUMMARY
# ===============================================================

total_time = time.time() - t0

prt(f"\n{'='*70}")
prt("=== GAP FADE - CONTRARY CANDLE STUDY COMPLETE ===")
prt(f"{'='*70}")
prt(f"  Total contrary candle events:  {len(results_df)}")
prt(f"  FT-confirmed events:           {len(results_df[results_df['has_ft']==True])}")
prt(f"  Unique tickers:                {results_df['ticker'].nunique()}")
if len(fade_ft) > 0:
    prt(f"  Gap-Up Fade WR (short):        {(fade_ft['eod_return'].dropna()>0).mean()*100:.1f}%  (n={len(fade_ft)})")
    prt(f"  Gap-Up Fade Avg Return:        {fade_ft['eod_return'].dropna().mean()*100:+.2f}%")
if len(bounce_ft) > 0:
    prt(f"  Gap-Dn Bounce WR (long):       {(bounce_ft['eod_return'].dropna()>0).mean()*100:.1f}%  (n={len(bounce_ft)})")
    prt(f"  Gap-Dn Bounce Avg Return:      {bounce_ft['eod_return'].dropna().mean()*100:+.2f}%")
prt(f"  API chunks:                    {total_calls} ({total_ok} ok, {total_fail} fail)")
prt(f"  Runtime:                       {total_time:.0f}s ({total_time/60:.1f} min)")
prt(f"{'='*70}")

# Re-save with final lines
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"\nDone. All outputs in: {OUTPUT_DIR}")

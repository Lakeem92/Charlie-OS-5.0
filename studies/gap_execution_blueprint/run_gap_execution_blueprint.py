## ═══════════════════════════════════════════════════════════════
## STUDY: Gap Day Execution Blueprint
## ═══════════════════════════════════════════════════════════════
## THE question: "When a stock gaps up 3%+ and opens with a neutral
## or bullish candle with follow-through, what does the REAL trade
## look like? Does the opening candle color matter? When is the LoD?
## When is the HoD? How far does it pull back before continuing?"
##
## This study exists to fix ONE problem: holding winners longer by
## replacing P&L anxiety with data-backed conviction.
## ═══════════════════════════════════════════════════════════════

import sys, os, time
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\indicators')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')

from shared.data_router import DataRouter
from shared.watchlist import get_watchlist
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

## ═══════════════════════════════════════════════════════════════
## CONFIGURATION
## ═══════════════════════════════════════════════════════════════

UNIVERSE = get_watchlist()
START_DATE = '2024-01-01'
END_DATE   = '2026-03-06'
GAP_THRESHOLD       = 0.02        # 2% minimum gap
ATR_PERIOD          = 14
FOLLOW_THROUGH_ATR_PCT = 0.40     # 40% of ATR above open = confirmed

# Market session times (Eastern)
SESSION_OPEN_ET  = "09:30"
SESSION_CLOSE_ET = "16:00"

## ═══════════════════════════════════════════════════════════════
## OPENING CANDLE CLASSIFICATION
## ═══════════════════════════════════════════════════════════════
## Mirrors what your EYES see on the TOS chart. No z-scores.
## No pre-gap contamination. Just: what does bar 1 look like?
##
## BULLISH:  close > open AND body > 40% of candle range
## NEUTRAL:  body <= 40% of candle range (doji/gray)
## BEARISH:  close < open AND body > 40% of candle range
## ═══════════════════════════════════════════════════════════════

def classify_candle(row):
    """Classify a candle the way you read the chart."""
    o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
    rng = h - l
    if rng == 0:
        return 'NEUTRAL'
    body = abs(c - o)
    body_pct = body / rng
    if body_pct <= 0.40:
        return 'NEUTRAL'
    elif c > o:
        return 'BULLISH'
    else:
        return 'BEARISH'

## ═══════════════════════════════════════════════════════════════
## STEP 1: FIND GAP DAYS + COMPUTE ATR
## ═══════════════════════════════════════════════════════════════

cache_dir = r'C:\QuantLab\Data_Lab\studies\gap_execution_blueprint\outputs'
os.makedirs(cache_dir, exist_ok=True)
cache_path = os.path.join(cache_dir, 'gap_events_cache.csv')

t0 = time.time()

# If Step 1 cache exists, skip the expensive daily scan
if os.path.exists(cache_path):
    print("=" * 70)
    print("STEP 1: Loading gap events from cache (delete gap_events_cache.csv to rescan)")
    print("=" * 70)
    gap_df = pd.read_csv(cache_path)
    print(f"Loaded {len(gap_df)} gap-up events (>= 2%) across {gap_df['ticker'].nunique()} tickers")
    print(f"Step 1 took {time.time()-t0:.1f}s (cached)")
else:
    print("=" * 70)
    print("STEP 1: Scanning for gap-up events >= 2% on watchlist names")
    print("=" * 70)

    all_gap_events = []
    skipped = 0
    processed = 0

    for i, ticker in enumerate(UNIVERSE):
        if (i + 1) % 25 == 0:
            print(f"  Scanning {i+1}/{len(UNIVERSE)} tickers... ({len(all_gap_events)} events found)")
        try:
            daily = DataRouter.get_price_data(ticker, START_DATE, end_date=END_DATE, timeframe='daily')
            if daily is None or len(daily) < ATR_PERIOD + 5:
                skipped += 1
                continue

            daily = daily.sort_index()

            # ATR calculation
            daily['prev_close'] = daily['Close'].shift(1)
            daily['tr'] = np.maximum(
                daily['High'] - daily['Low'],
                np.maximum(
                    abs(daily['High'] - daily['prev_close']),
                    abs(daily['Low'] - daily['prev_close'])
                )
            )
            daily['atr'] = daily['tr'].rolling(ATR_PERIOD).mean()

            # Gap calculation
            daily['gap_pct'] = (daily['Open'] - daily['prev_close']) / daily['prev_close']

            for idx in range(ATR_PERIOD + 1, len(daily)):
                row = daily.iloc[idx]

                # Skip if core inputs fail
                if pd.isna(row['gap_pct']) or pd.isna(row['atr']):
                    continue
                if row['gap_pct'] < GAP_THRESHOLD:
                    continue

                all_gap_events.append({
                    'ticker': ticker,
                    'date': daily.index[idx],
                    'prev_close': row['prev_close'],
                    'open_price': row['Open'],
                    'day_high': row['High'],
                    'day_low': row['Low'],
                    'day_close': row['Close'],
                    'gap_pct': row['gap_pct'],
                    'atr': row['atr'],
                    'follow_through_level': row['Open'] + (row['atr'] * FOLLOW_THROUGH_ATR_PCT)
                })
            processed += 1
        except Exception as e:
            skipped += 1
            continue

    gap_df = pd.DataFrame(all_gap_events)
    if len(gap_df) == 0:
        print("\n⚠️  No gap events found. Check watchlist, date range, or data connectivity.")
        sys.exit(0)
    print(f"\nFound {len(gap_df)} gap-up events (>= 2%) across {gap_df['ticker'].nunique()} tickers")
    print(f"Processed: {processed} | Skipped: {skipped}")
    print(f"Step 1 took {time.time()-t0:.1f}s")

    gap_df.to_csv(cache_path, index=False)
    print(f"Gap events cached to {cache_dir}")

## ═══════════════════════════════════════════════════════════════
## STEP 2: PER-TICKER INTRADAY CACHE, CLASSIFY, AND MEASURE
## ═══════════════════════════════════════════════════════════════
## Pull 5-min data per-TICKER in smart date-range chunks (max 10K
## bars each ≈ 6 months). Only pull chunks that cover that ticker's
## actual event dates. fallback=False → instant skip on failure.
## Then slice event days from the in-memory cache.
## ═══════════════════════════════════════════════════════════════

t1 = time.time()
print("\n" + "=" * 70)
print("STEP 2: Building per-ticker intraday cache (no fallback)")
print("=" * 70)

# Group events by ticker and find date ranges
events_by_ticker = defaultdict(list)
for _, event in gap_df.iterrows():
    events_by_ticker[event['ticker']].append(pd.Timestamp(event['date']))

CHUNK_DAYS = 120  # ~6 months of trading days; safely under 10K bar limit

ticker_cache = {}  # ticker → full DataFrame (sorted, Eastern TZ, all bars)
total_calls = 0
total_ok = 0
total_fail = 0

for i, (ticker, event_dates) in enumerate(sorted(events_by_ticker.items())):
    if (i + 1) % 25 == 0 or (i + 1) == len(events_by_ticker):
        elapsed = time.time() - t1
        print(f"  Ticker {i+1}/{len(events_by_ticker)} | {total_ok} chunks ok, {total_fail} fail | {elapsed:.0f}s")

    min_dt = min(event_dates) - timedelta(days=1)
    max_dt = max(event_dates) + timedelta(days=1)

    # Generate 6-month chunk windows covering [min_dt, max_dt]
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

# ── Now process each event from the cache (pure memory, no API) ──

results = []
no_data = 0
total = len(gap_df)

for i, (idx, event) in enumerate(gap_df.iterrows()):
    if (i + 1) % 2000 == 0 or (i + 1) == total:
        print(f"  Processing event {i+1}/{total}... ({len(results)} valid so far)")

    try:
        ticker = event['ticker']
        event_date = pd.Timestamp(event['date'])
        date_str = event_date.strftime('%Y-%m-%d')

        # Slice the event day from cached ticker data
        ticker_intraday = ticker_cache.get(ticker)
        if ticker_intraday is None:
            no_data += 1
            continue

        intraday = ticker_intraday[ticker_intraday.index.date == event_date.date()]
        if intraday is None or len(intraday) < 20:
            no_data += 1
            continue

        session = intraday.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
        if len(session) < 10:
            no_data += 1
            continue

        # ─── OPENING CANDLE (first 5-min bar) ───
        bar1 = session.iloc[0]
        candle_color = classify_candle(bar1)

        # Skip bearish opens — we only care about neutral and bullish
        if candle_color == 'BEARISH':
            results.append({
                'ticker': ticker,
                'date': event_date,
                'gap_pct': event['gap_pct'],
                'open_price': event['open_price'],
                'atr': event['atr'],
                'candle_color': 'BEARISH',
                'has_follow_through': False,
                'included_in_analysis': False
            })
            continue

        # ─── FOLLOW-THROUGH CHECK ───
        # Does any 5-min CLOSE reach 40% of ATR above the open?
        ft_level = event['follow_through_level']
        session_closes = session['Close']
        has_ft = (session_closes >= ft_level).any()

        if not has_ft:
            results.append({
                'ticker': ticker,
                'date': event_date,
                'gap_pct': event['gap_pct'],
                'open_price': event['open_price'],
                'atr': event['atr'],
                'candle_color': candle_color,
                'has_follow_through': False,
                'included_in_analysis': False
            })
            continue

        # ─── FOLLOW-THROUGH BAR (entry point proxy) ───
        # First bar where Close >= follow-through level
        ft_bar_idx = None
        for j in range(len(session)):
            if session.iloc[j]['Close'] >= ft_level:
                ft_bar_idx = j
                break

        if ft_bar_idx is None:
            continue

        entry_price = session.iloc[ft_bar_idx]['Close']
        entry_time = session.index[ft_bar_idx]

        # ─── POST-ENTRY SESSION DATA ───
        post_entry = session.iloc[ft_bar_idx:]
        full_session = session

        # EOD return from entry
        eod_close = session.iloc[-1]['Close']
        eod_return = (eod_close - entry_price) / entry_price

        # ─── LOW OF DAY ANALYSIS ───
        lod_price = full_session['Low'].min()
        lod_bar_idx = full_session['Low'].idxmin()
        lod_time = lod_bar_idx
        session_open_time = full_session.index[0]
        if hasattr(lod_time, 'hour'):
            lod_minutes_from_open = (lod_time - session_open_time).total_seconds() / 60
        else:
            lod_minutes_from_open = 0

        # Is LoD set before or after entry?
        lod_before_entry = lod_time <= entry_time

        # After entry, does a NEW low get set below entry?
        post_entry_low = post_entry['Low'].min() if len(post_entry) > 0 else entry_price
        new_low_after_entry = post_entry_low < entry_price

        # ─── HIGH OF DAY ANALYSIS ───
        hod_price = full_session['High'].max()
        hod_bar_idx = full_session['High'].idxmax()
        hod_time = hod_bar_idx
        if hasattr(hod_time, 'hour'):
            hod_minutes_from_open = (hod_time - session_open_time).total_seconds() / 60
        else:
            hod_minutes_from_open = 0

        # ─── MAX ADVERSE EXCURSION (from entry) ───
        if len(post_entry) > 0:
            mae_price = post_entry['Low'].min()
            mae_pct = (mae_price - entry_price) / entry_price
        else:
            mae_pct = 0

        # ─── MAX FAVORABLE EXCURSION (from entry) ───
        if len(post_entry) > 0:
            mfe_price = post_entry['High'].max()
            mfe_pct = (mfe_price - entry_price) / entry_price
        else:
            mfe_pct = 0

        # ─── FORWARD RETURNS AT INTERVALS (from entry bar) ───
        fwd_returns = {}
        for label, bars in [('15min', 3), ('30min', 6), ('1hr', 12), ('2hr', 24)]:
            target = ft_bar_idx + bars
            if target < len(session):
                fwd_returns[f'fwd_{label}'] = (session.iloc[target]['Close'] - entry_price) / entry_price
            else:
                fwd_returns[f'fwd_{label}'] = eod_return  # Use EOD if not enough bars

        # ─── POST-30-MIN NEW LOW CHECK ───
        first_30_min = session.iloc[:6] if len(session) >= 6 else session
        first_30_low = first_30_min['Low'].min()
        after_30_min = session.iloc[6:] if len(session) > 6 else pd.DataFrame()
        if len(after_30_min) > 0:
            new_low_after_30 = after_30_min['Low'].min() < first_30_low
        else:
            new_low_after_30 = False

        # ─── PULLBACK BEFORE CONTINUATION ───
        if len(post_entry) > 1:
            running_low = entry_price
            max_pullback_before_new_high = 0
            hit_new_high = False
            for j in range(1, len(post_entry)):
                bar_low = post_entry.iloc[j]['Low']
                bar_high = post_entry.iloc[j]['High']
                running_low = min(running_low, bar_low)
                pullback = (running_low - entry_price) / entry_price
                if bar_high > entry_price * 1.001:  # New high above entry
                    max_pullback_before_new_high = pullback
                    hit_new_high = True
                    break
            if not hit_new_high:
                max_pullback_before_new_high = (running_low - entry_price) / entry_price
        else:
            max_pullback_before_new_high = 0

        results.append({
            'ticker': ticker,
            'date': event_date,
            'gap_pct': event['gap_pct'],
            'open_price': event['open_price'],
            'atr': event['atr'],
            'candle_color': candle_color,
            'has_follow_through': True,
            'included_in_analysis': True,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'eod_close': eod_close,
            'eod_return': eod_return,
            'lod_price': lod_price,
            'lod_time': lod_time,
            'lod_minutes_from_open': lod_minutes_from_open,
            'lod_before_entry': lod_before_entry,
            'hod_price': hod_price,
            'hod_time': hod_time,
            'hod_minutes_from_open': hod_minutes_from_open,
            'mae_pct': mae_pct,
            'mfe_pct': mfe_pct,
            'new_low_after_entry': new_low_after_entry,
            'new_low_after_30min': new_low_after_30,
            'max_pullback_before_new_high': max_pullback_before_new_high,
            **fwd_returns
        })

    except Exception as e:
        no_data += 1
        continue

results_df = pd.DataFrame(results)
if len(results_df) == 0 or 'included_in_analysis' not in results_df.columns:
    print("\n⚠️  No results produced. Check intraday data availability.")
    sys.exit(0)
analysis = results_df[results_df['included_in_analysis'] == True].copy()

print(f"\nTotal gap events scanned: {total}")
print(f"Bearish opens (excluded): {len(results_df[results_df['candle_color'] == 'BEARISH'])}")
no_ft = len(results_df[(results_df['has_follow_through'] == False) & (results_df['candle_color'] != 'BEARISH')])
print(f"No follow-through (excluded): {no_ft}")
print(f"No intraday data: {no_data}")
print(f"═══ INCLUDED IN ANALYSIS: {len(analysis)} events ═══")
print(f"Step 2 took {time.time()-t1:.1f}s")

## ═══════════════════════════════════════════════════════════════
## STEP 3: THE ANSWERS
## ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("═══ QUESTION 1: Does Opening Candle Color Matter? ═══")
print("=" * 70)

for color in ['BULLISH', 'NEUTRAL']:
    group = analysis[analysis['candle_color'] == color]
    n = len(group)
    if n == 0:
        print(f"\n  {color}: No events found")
        continue

    eod = group['eod_return'].dropna()
    winners = eod[eod > 0]
    losers = eod[eod <= 0]

    print(f"\n  ── {color} OPENS (n={n}) ──")
    print(f"  EOD Win Rate:     {(eod > 0).mean() * 100:.1f}%")
    print(f"  EOD Avg Return:   {eod.mean() * 100:+.2f}%")
    print(f"  EOD Median Return:{eod.median() * 100:+.2f}%")
    if len(winners) > 0:
        print(f"  Avg Winner:       {winners.mean() * 100:+.2f}% (n={len(winners)})")
    if len(losers) > 0:
        print(f"  Avg Loser:        {losers.mean() * 100:+.2f}% (n={len(losers)})")

    for col, label in [('fwd_15min', '15min'), ('fwd_30min', '30min'),
                        ('fwd_1hr', '1hr'), ('fwd_2hr', '2hr')]:
        vals = group[col].dropna()
        if len(vals) > 0:
            print(f"  {label:>6s} fwd return: {vals.mean()*100:+.2f}% | Win Rate: {(vals>0).mean()*100:.1f}%")

# Combined baseline
print(f"\n  ── ALL (BULLISH + NEUTRAL) COMBINED (n={len(analysis)}) ──")
eod_all = analysis['eod_return'].dropna()
print(f"  EOD Win Rate:     {(eod_all > 0).mean() * 100:.1f}%")
print(f"  EOD Avg Return:   {eod_all.mean() * 100:+.2f}%")

print("\n" + "=" * 70)
print("═══ QUESTION 2: When Is the Low of Day Set? ═══")
print("=" * 70)
print("(Times shown in minutes from market open — subtract 60 for CT)")

for color in ['BULLISH', 'NEUTRAL', 'ALL']:
    if color == 'ALL':
        group = analysis
    else:
        group = analysis[analysis['candle_color'] == color]
    n = len(group)
    if n == 0:
        continue

    lod_mins = group['lod_minutes_from_open'].dropna()

    print(f"\n  ── {color} (n={n}) ──")
    print(f"  Avg LoD time:    {lod_mins.mean():.0f} min from open ({int(lod_mins.mean())//60}h {int(lod_mins.mean())%60}m)")
    print(f"  Median LoD time: {lod_mins.median():.0f} min from open ({int(lod_mins.median())//60}h {int(lod_mins.median())%60}m)")

    # LoD timing buckets
    in_first_5 = (lod_mins <= 5).mean() * 100
    in_first_15 = (lod_mins <= 15).mean() * 100
    in_first_30 = (lod_mins <= 30).mean() * 100
    in_first_60 = (lod_mins <= 60).mean() * 100
    after_first_hour = (lod_mins > 60).mean() * 100

    print(f"  LoD in first 5 min:   {in_first_5:.1f}%")
    print(f"  LoD in first 15 min:  {in_first_15:.1f}%")
    print(f"  LoD in first 30 min:  {in_first_30:.1f}%")
    print(f"  LoD in first 60 min:  {in_first_60:.1f}%")
    print(f"  LoD AFTER first hour:  {after_first_hour:.1f}%")

    # Does a new low form after the first 30 min?
    new_low_30 = group['new_low_after_30min'].mean() * 100
    print(f"  New session low AFTER first 30 min: {new_low_30:.1f}%")

    # Does price go below entry after entry?
    below_entry = group['new_low_after_entry'].mean() * 100
    print(f"  Price goes below ENTRY after follow-through: {below_entry:.1f}%")

print("\n" + "=" * 70)
print("═══ QUESTION 3: When Is the High of Day Set? ═══")
print("=" * 70)

for color in ['BULLISH', 'NEUTRAL', 'ALL']:
    if color == 'ALL':
        group = analysis
    else:
        group = analysis[analysis['candle_color'] == color]
    n = len(group)
    if n == 0:
        continue

    hod_mins = group['hod_minutes_from_open'].dropna()

    print(f"\n  ── {color} (n={n}) ──")
    print(f"  Avg HoD time:    {hod_mins.mean():.0f} min from open ({int(hod_mins.mean())//60}h {int(hod_mins.mean())%60}m)")
    print(f"  Median HoD time: {hod_mins.median():.0f} min from open ({int(hod_mins.median())//60}h {int(hod_mins.median())%60}m)")

    in_first_30 = (hod_mins <= 30).mean() * 100
    in_first_60 = (hod_mins <= 60).mean() * 100
    in_first_2hr = (hod_mins <= 120).mean() * 100
    in_last_hour = (hod_mins >= 330).mean() * 100  # Last hour = 5.5hrs+ from open

    print(f"  HoD in first 30 min:  {in_first_30:.1f}%")
    print(f"  HoD in first 60 min:  {in_first_60:.1f}%")
    print(f"  HoD in first 2 hrs:   {in_first_2hr:.1f}%")
    print(f"  HoD in last hour:     {in_last_hour:.1f}%")

print("\n" + "=" * 70)
print("═══ QUESTION 4: What Does the Real P&L Look Like? ═══")
print("(Max Adverse Excursion = worst pullback from entry while holding)")
print("=" * 70)

for color in ['BULLISH', 'NEUTRAL', 'ALL']:
    if color == 'ALL':
        group = analysis
    else:
        group = analysis[analysis['candle_color'] == color]
    n = len(group)
    if n == 0:
        continue

    mae = group['mae_pct'].dropna()
    mfe = group['mfe_pct'].dropna()
    pullback = group['max_pullback_before_new_high'].dropna()

    print(f"\n  ── {color} (n={n}) ──")
    print(f"  Max Adverse Excursion (avg):    {mae.mean()*100:+.2f}%  (this is how far it drops from your entry)")
    print(f"  Max Adverse Excursion (median): {mae.median()*100:+.2f}%")
    print(f"  Max Adverse Excursion (worst 10%): {mae.quantile(0.10)*100:+.2f}%")
    print(f"  Max Favorable Excursion (avg):  {mfe.mean()*100:+.2f}%  (this is how far it runs in your favor)")
    print(f"  Max Favorable Excursion (median):{mfe.median()*100:+.2f}%")
    print(f"  Avg pullback before new high:   {pullback.mean()*100:+.2f}%")
    print(f"  Median pullback before new high:{pullback.median()*100:+.2f}%")

    # Risk/Reward profile
    group_winners = group[group['eod_return'] > 0]['eod_return']
    group_losers = group[group['eod_return'] <= 0]['eod_return']
    avg_winner = group_winners.mean() * 100 if len(group_winners) > 0 else 0
    avg_loser = group_losers.mean() * 100 if len(group_losers) > 0 else 0
    if avg_loser != 0:
        rr_ratio = abs(avg_winner / avg_loser)
    else:
        rr_ratio = float('inf')
    print(f"  Risk/Reward Ratio:              {rr_ratio:.2f}:1 (avg winner / avg loser)")

print("\n" + "=" * 70)
print("═══ QUESTION 5: Gap Size Matters? ═══")
print("(Split by gap magnitude to see if bigger gaps behave differently)")
print("=" * 70)

for low, high, label in [(0.03, 0.05, '3-5%'), (0.05, 0.08, '5-8%'),
                           (0.08, 0.12, '8-12%'), (0.12, 0.20, '12-20%'),
                           (0.20, 1.0, '20%+')]:
    group = analysis[(analysis['gap_pct'] >= low) & (analysis['gap_pct'] < high)]
    n = len(group)
    if n < 5:
        continue

    eod = group['eod_return'].dropna()
    mae = group['mae_pct'].dropna()
    lod_mins = group['lod_minutes_from_open'].dropna()

    print(f"\n  Gap {label} (n={n}):")
    print(f"    EOD Win Rate: {(eod > 0).mean()*100:.1f}% | Avg Return: {eod.mean()*100:+.2f}%")
    print(f"    Avg MAE: {mae.mean()*100:+.2f}% | Avg LoD: {lod_mins.mean():.0f} min from open")
    lod_30 = (lod_mins <= 30).mean() * 100
    print(f"    LoD in first 30 min: {lod_30:.1f}%")

## ═══════════════════════════════════════════════════════════════
## STEP 4: SAVE EVERYTHING
## ═══════════════════════════════════════════════════════════════

results_df.to_csv(os.path.join(cache_dir, 'all_gap_events_classified.csv'), index=False)
analysis.to_csv(os.path.join(cache_dir, 'execution_blueprint_events.csv'), index=False)

total_time = time.time() - t0
print(f"\n✅ All data saved to {cache_dir}")
print(f"Total runtime: {total_time:.0f}s ({total_time/60:.1f} min)")

## ═══════════════════════════════════════════════════════════════
## INTERPRETATION GUIDE
## ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("═══ HOW TO USE THESE RESULTS ═══")
print("=" * 70)
print("""
MID-TRADE CONVICTION RULES (tape this to your desk):

1. CANDLE COLOR AT OPEN:
   If BULLISH and NEUTRAL win rates are within 5% of each other
   → Color is noise. The follow-through is the signal. Stop hesitating.

2. LOW OF DAY TIMING:
   If LoD is set in first 30 min X% of the time
   → After 9:00 AM CT, the low is probably IN. Hold.
   
3. MAX ADVERSE EXCURSION:
   If the average pullback from entry is X%
   → Any pullback smaller than X% is NORMAL. It's not your exit signal.
   → Only react to pullbacks in the worst 10% (that's the real danger zone).

4. HIGH OF DAY TIMING:
   If HoD is set at [time] on average
   → Don't take profits before that time unless structure breaks.
   
5. POST-30-MIN NEW LOW:
   If new lows after 30 min happen only X% of the time
   → After the first 30 min, your downside risk is statistically bounded.
   → HOLD unless a structural level breaks.
""")

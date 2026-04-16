## ═══════════════════════════════════════════════════════════════
## STUDY: Gap Day Execution Blueprint — Extended Analysis
## ═══════════════════════════════════════════════════════════════
## Tasks:
## 1. Fix data bug: 'Price below entry after FT' metric
## 2. Sections A-E: Pullback, Session High, Entry Timing,
##    Hold Time, R:R Comparison
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
FOLLOW_THROUGH_ATR_PCT = 0.40
CHUNK_DAYS = 120

# ET times for hold-time analysis (minutes from 9:30 ET open)
# CT = ET - 1 hour, so market open = 8:30 CT
HOLD_TIMES_ET = {
    '9:30 CT (10:30 ET)':  60,
    '10:00 CT (11:00 ET)': 90,
    '10:30 CT (11:30 ET)': 120,
    '11:00 CT (12:00 ET)': 150,
    '11:30 CT (12:30 ET)': 180,
    '12:00 CT (13:00 ET)': 210,
}

# HoD timing buckets (minutes from 9:30 ET open)
HOD_BUCKETS = [
    ('8:30-9:00 CT',         0,   30),
    ('9:00-9:30 CT',         30,  60),
    ('9:30-10:00 CT',        60,  90),
    ('10:00-10:30 CT',       90,  120),
    ('10:30-11:30 CT',       120, 180),
    ('11:30+ CT',            180, 999),
    ('Final hour (2-3 CT)',  330, 390),
]

GAP_BUCKETS = [
    ('2-5%',  0.02, 0.05),
    ('5-8%',  0.05, 0.08),
    ('8-12%', 0.08, 0.12),
    ('12%+',  0.12, 1.00),
]

## ═══════════════════════════════════════════════════════════════
## STEP 1: LOAD EXISTING STUDY RESULTS
## ═══════════════════════════════════════════════════════════════

t0 = time.time()
print("=" * 70)
print("STEP 1: Loading existing study results")
print("=" * 70)

results_df = pd.read_csv(RESULTS_CSV)
gap_cache_df = pd.read_csv(GAP_CACHE_CSV)

# Build lookup for ATR / follow-through level
gap_lookup = {}
for _, row in gap_cache_df.iterrows():
    key = (row['ticker'], str(row['date'])[:10])
    gap_lookup[key] = {
        'atr': row['atr'],
        'follow_through_level': row['follow_through_level'],
        'open_price': row['open_price'],
        'prev_close': row['prev_close'],
        'gap_pct': row['gap_pct']
    }

analysis_df = results_df.copy()
print(f"Loaded {len(analysis_df)} events from execution_blueprint_events.csv")
print(f"Unique tickers: {analysis_df['ticker'].nunique()}")

# Record old bug stat from README
OLD_BUG_STAT = 0.0  # README reported 0.0% / 0.1%

## ═══════════════════════════════════════════════════════════════
## STEP 2: BUILD PER-TICKER INTRADAY CACHE
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
        print(f"  Ticker {i+1}/{len(events_by_ticker)} | {total_ok} chunks ok, "
              f"{total_fail} fail | {elapsed:.0f}s")

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
## STEP 3: PROCESS EACH EVENT — COMPUTE ALL EXTENDED METRICS
## ═══════════════════════════════════════════════════════════════

t2 = time.time()
print("=" * 70)
print("STEP 3: Computing extended metrics for each event")
print("=" * 70)

extended_results = []
skipped = 0
total_events = len(analysis_df)

for i, (idx, event) in enumerate(analysis_df.iterrows()):
    if (i + 1) % 500 == 0 or (i + 1) == total_events:
        print(f"  Processing {i+1}/{total_events}... ({len(extended_results)} valid)")

    try:
        ticker = event['ticker']
        event_date = pd.Timestamp(event['date'])
        date_str = str(event_date)[:10]
        candle_color = event['candle_color']
        gap_pct = event['gap_pct']

        # Get session bars
        ticker_intraday = ticker_cache.get(ticker)
        if ticker_intraday is None:
            skipped += 1
            continue

        day_bars = ticker_intraday[ticker_intraday.index.date == event_date.date()]
        if day_bars is None or len(day_bars) < 20:
            skipped += 1
            continue

        session = day_bars.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
        if len(session) < 10:
            skipped += 1
            continue

        # Re-detect follow-through bar
        gap_key = (ticker, date_str)
        gap_info = gap_lookup.get(gap_key)
        if gap_info is None:
            # Try alternate key formats
            for k, v in gap_lookup.items():
                if k[0] == ticker and date_str in str(k[1]):
                    gap_info = v
                    break
        if gap_info is None:
            skipped += 1
            continue

        ft_level = gap_info['follow_through_level']
        atr = gap_info['atr']

        ft_bar_idx = None
        for j in range(len(session)):
            if session.iloc[j]['Close'] >= ft_level:
                ft_bar_idx = j
                break

        if ft_bar_idx is None:
            skipped += 1
            continue

        entry_price = session.iloc[ft_bar_idx]['Close']
        entry_high = session.iloc[ft_bar_idx]['High']
        entry_low = session.iloc[ft_bar_idx]['Low']
        entry_time = session.index[ft_bar_idx]
        session_open_time = session.index[0]

        # Bars strictly AFTER entry (for bug fix and post-entry analysis)
        after_entry = session.iloc[ft_bar_idx + 1:]
        # All bars from entry onward (for MAE/MFE that includes entry bar)
        from_entry = session.iloc[ft_bar_idx:]
        eod_close = session.iloc[-1]['Close']
        eod_return = (eod_close - entry_price) / entry_price

        # ═══════════════════════════════════════════════════
        # BUG FIX: Price below entry after follow-through
        # Uses ONLY bars strictly after the entry bar,
        # checking each bar's LOW against entry_price
        # ═══════════════════════════════════════════════════
        if len(after_entry) > 0:
            price_below_entry_after_ft = bool((after_entry['Low'] < entry_price).any())
        else:
            price_below_entry_after_ft = False

        # ═══════════════════════════════════════════════════
        # SECTION A: PULLBACK BEHAVIOR AFTER FOLLOW-THROUGH
        # ═══════════════════════════════════════════════════

        # Find the session high AFTER entry
        if len(after_entry) > 0:
            after_entry_high_max = after_entry['High'].max()
            session_high_price = max(entry_high, after_entry_high_max)
            if after_entry_high_max >= entry_high:
                session_high_time = after_entry['High'].idxmax()
                # Find the global bar index of the session high
                session_high_bar = None
                for j2 in range(len(session)):
                    if session.index[j2] == session_high_time:
                        session_high_bar = j2
                        break
                if session_high_bar is None:
                    session_high_bar = ft_bar_idx
            else:
                session_high_time = entry_time
                session_high_bar = ft_bar_idx
        else:
            session_high_price = entry_high
            session_high_time = entry_time
            session_high_bar = ft_bar_idx

        # A1: Did price pull back below entry before reaching session high?
        a1_pullback_before_high = False
        # A2: Deepest pullback from entry price, before session high
        a2_deepest_pullback = 0.0
        a2_deepest_pullback_bar_idx = 0
        a2_deepest_pullback_minutes = 0.0
        running_low = entry_price

        if len(after_entry) > 0:
            for j2 in range(len(after_entry)):
                bar = after_entry.iloc[j2]
                bar_time = after_entry.index[j2]
                # Only look at bars BEFORE or AT the session high time
                if bar_time > session_high_time:
                    break
                if bar['Low'] < entry_price:
                    a1_pullback_before_high = True
                running_low = min(running_low, bar['Low'])
                pullback_pct = (running_low - entry_price) / entry_price
                if pullback_pct < a2_deepest_pullback:
                    a2_deepest_pullback = pullback_pct
                    a2_deepest_pullback_bar_idx = j2
                    a2_deepest_pullback_minutes = (bar_time - entry_time).total_seconds() / 60.0

        # A3: Pullback timing
        a3_pb_bar_idx = a2_deepest_pullback_bar_idx
        a3_pb_minutes = a2_deepest_pullback_minutes

        # A4: After pullback, did price recover above FT bar's high?
        a4_recovered = False
        if len(after_entry) > 0:
            a4_recovered = bool((after_entry['High'] > entry_high).any())

        # ═══════════════════════════════════════════════════
        # SECTION B: SESSION HIGH BEHAVIOR
        # ═══════════════════════════════════════════════════

        # B1: Max drawdown from session high before EOD
        b1_drawdown_from_high = 0.0
        if session_high_bar is not None and session_high_bar < len(session) - 1:
            bars_after_high = session.iloc[session_high_bar + 1:]
            if len(bars_after_high) > 0:
                min_after_high = bars_after_high['Low'].min()
                if session_high_price > 0:
                    b1_drawdown_from_high = (min_after_high - session_high_price) / session_high_price

        # B2: Multiple HoD attempts
        b2_multiple_hod = False
        if len(after_entry) > 0 and session_high_price > 0:
            threshold_touch = session_high_price * 0.998
            threshold_retreat = session_high_price * 0.990
            touched_high = False
            retreated = False
            for j2 in range(len(after_entry)):
                bar = after_entry.iloc[j2]
                if bar['High'] >= threshold_touch:
                    if touched_high and retreated:
                        b2_multiple_hod = True
                        break
                    touched_high = True
                    retreated = False
                elif touched_high and bar['High'] < threshold_retreat:
                    retreated = True

        # B3: HoD timing (minutes from open)
        hod_minutes_from_open = (session_high_time - session_open_time).total_seconds() / 60.0

        # ═══════════════════════════════════════════════════
        # SECTION C: ENTRY TIMING ANALYSIS
        # ═══════════════════════════════════════════════════

        # E1: Breakout entry (existing FT bar close)
        e1_entry = entry_price
        e1_mae = (from_entry['Low'].min() - entry_price) / entry_price if len(from_entry) > 0 else 0.0
        e1_mfe = (from_entry['High'].max() - entry_price) / entry_price if len(from_entry) > 0 else 0.0
        e1_eod_return = eod_return

        # E2: First Pullback Entry
        e2_entry = np.nan
        e2_mae = np.nan
        e2_mfe = np.nan
        e2_eod_return = np.nan
        e2_price_improvement = np.nan
        e2_cheaper = False
        e2_found = False

        if len(after_entry) >= 2:
            prev_close = entry_price  # start from entry bar close
            for j2 in range(len(after_entry)):
                curr_bar = after_entry.iloc[j2]
                # Check for pullback: current close < previous close
                if curr_bar['Close'] < prev_close:
                    # Look for recovery: next bar closes higher
                    if j2 + 1 < len(after_entry):
                        next_bar = after_entry.iloc[j2 + 1]
                        if next_bar['Close'] > curr_bar['Close']:
                            e2_entry = next_bar['Close']
                            # Global index for the recovery bar
                            e2_bar_global = ft_bar_idx + 1 + j2 + 1
                            remaining = session.iloc[e2_bar_global:]
                            if len(remaining) > 0:
                                e2_mae = (remaining['Low'].min() - e2_entry) / e2_entry
                                e2_mfe = (remaining['High'].max() - e2_entry) / e2_entry
                            e2_eod_return = (eod_close - e2_entry) / e2_entry
                            e2_price_improvement = (e1_entry - e2_entry) / e1_entry
                            e2_cheaper = bool(e2_entry < e1_entry)
                            e2_found = True
                            break
                prev_close = curr_bar['Close']

        # E3: Deepest Pullback Entry
        e3_entry = np.nan
        e3_mae = np.nan
        e3_mfe = np.nan
        e3_eod_return = np.nan
        e3_price_improvement = np.nan
        e3_cheaper = False
        e3_found = False

        if len(after_entry) > 0 and session_high_bar is not None:
            # Collect bars between entry and session high (exclusive of entry bar)
            bars_to_high_indices = []
            for j2 in range(len(after_entry)):
                bar_time = after_entry.index[j2]
                if bar_time >= session_high_time:
                    break
                bars_to_high_indices.append(j2)

            if len(bars_to_high_indices) > 0:
                lowest_close = float('inf')
                lowest_close_after_idx = -1
                for j2 in bars_to_high_indices:
                    c = after_entry.iloc[j2]['Close']
                    if c < lowest_close:
                        lowest_close = c
                        lowest_close_after_idx = j2

                if lowest_close_after_idx >= 0 and lowest_close < float('inf'):
                    e3_entry = lowest_close
                    e3_bar_global = ft_bar_idx + 1 + lowest_close_after_idx
                    remaining = session.iloc[e3_bar_global:]
                    if len(remaining) > 0:
                        e3_mae = (remaining['Low'].min() - e3_entry) / e3_entry
                        e3_mfe = (remaining['High'].max() - e3_entry) / e3_entry
                    e3_eod_return = (eod_close - e3_entry) / e3_entry
                    e3_price_improvement = (e1_entry - e3_entry) / e1_entry
                    e3_cheaper = bool(e3_entry < e1_entry)
                    e3_found = True

        # ═══════════════════════════════════════════════════
        # SECTION D: HOLD TIME — prices at specific times
        # ═══════════════════════════════════════════════════
        hold_prices = {}
        entry_bar_minutes_from_open = (entry_time - session_open_time).total_seconds() / 60.0
        for label, target_min in HOLD_TIMES_ET.items():
            if target_min <= entry_bar_minutes_from_open:
                hold_prices[label] = entry_price
            else:
                target_time = session_open_time + pd.Timedelta(minutes=target_min)
                valid = session[session.index <= target_time]
                if len(valid) > 0:
                    hold_prices[label] = valid.iloc[-1]['Close']
                else:
                    hold_prices[label] = entry_price

        # Compute hold returns and MFE capture %
        hold_returns = {}
        hold_mfe_pcts = {}
        mfe_price = from_entry['High'].max() if len(from_entry) > 0 else entry_price
        full_mfe = (mfe_price - entry_price) / entry_price if entry_price > 0 else 0.0
        for label, price in hold_prices.items():
            ret = (price - entry_price) / entry_price
            hold_returns[label] = ret
            if full_mfe > 0:
                hold_mfe_pcts[label] = (ret / full_mfe) * 100.0
            else:
                hold_mfe_pcts[label] = 0.0

        # ═══ BUILD RESULT ROW ═══
        row = {
            'ticker': ticker,
            'date': date_str,
            'gap_pct': gap_pct,
            'candle_color': candle_color,
            'entry_price': entry_price,
            'eod_close': eod_close,
            'eod_return': eod_return,
            'atr': atr,
            # Bug fix
            'price_below_entry_after_ft': price_below_entry_after_ft,
            # Section A
            'a1_pullback_before_high': a1_pullback_before_high,
            'a2_deepest_pullback_pct': a2_deepest_pullback,
            'a3_pullback_bar_idx': a3_pb_bar_idx,
            'a3_pullback_minutes': a3_pb_minutes,
            'a4_recovered_above_ft_high': a4_recovered,
            # Section B
            'b1_drawdown_from_session_high': b1_drawdown_from_high,
            'b2_multiple_hod_attempts': b2_multiple_hod,
            'hod_minutes_from_open': hod_minutes_from_open,
            'session_high_price': session_high_price,
            # Section C — E1
            'e1_entry': e1_entry,
            'e1_mae': e1_mae,
            'e1_mfe': e1_mfe,
            'e1_eod_return': e1_eod_return,
            # Section C — E2
            'e2_found': e2_found,
            'e2_entry': e2_entry,
            'e2_mae': e2_mae,
            'e2_mfe': e2_mfe,
            'e2_eod_return': e2_eod_return,
            'e2_price_improvement': e2_price_improvement,
            'e2_cheaper': e2_cheaper,
            # Section C — E3
            'e3_found': e3_found,
            'e3_entry': e3_entry,
            'e3_mae': e3_mae,
            'e3_mfe': e3_mfe,
            'e3_eod_return': e3_eod_return,
            'e3_price_improvement': e3_price_improvement,
            'e3_cheaper': e3_cheaper,
            # Section D
            'full_mfe_pct': full_mfe,
        }
        # Add hold returns + MFE pct columns
        for label, ret in hold_returns.items():
            safe = label.split(' ')[0].replace(':', '')
            row[f'hold_return_{safe}'] = ret
        for label, pct in hold_mfe_pcts.items():
            safe = label.split(' ')[0].replace(':', '')
            row[f'hold_mfe_pct_{safe}'] = pct

        extended_results.append(row)

    except Exception as e:
        skipped += 1
        continue

print(f"\nProcessed: {len(extended_results)} | Skipped: {skipped}")
print(f"Step 3 took {time.time()-t2:.1f}s")

## ═══════════════════════════════════════════════════════════════
## STEP 4: AGGREGATE AND PRINT ALL RESULTS
## ═══════════════════════════════════════════════════════════════

ext = pd.DataFrame(extended_results)
if len(ext) == 0:
    print("\n⚠️  No results produced. Check data availability.")
    sys.exit(0)

output_lines = []

def prt(line=""):
    print(line)
    output_lines.append(line)


prt("\n" + "=" * 70)
prt("═══ EXTENDED ANALYSIS RESULTS ═══")
prt("=" * 70)

# ── BUG FIX ──
corrected_stat = ext['price_below_entry_after_ft'].mean() * 100
prt(f"\n┌─ BUG FIX: Price below entry after follow-through ─────────┐")
prt(f"│  OLD stat (from README):  {OLD_BUG_STAT:.1f}%                             │")
prt(f"│  CORRECTED stat:          {corrected_stat:.1f}%                            │")
prt(f"│  (checking Low of bars strictly AFTER entry bar)           │")
prt(f"└────────────────────────────────────────────────────────────┘")

# ═══ SECTION A: PULLBACK BEHAVIOR ═══
prt("\n" + "=" * 70)
prt("═══ SECTION A: PULLBACK BEHAVIOR AFTER FOLLOW-THROUGH ═══")
prt("=" * 70)

# A1
a1_pct = ext['a1_pullback_before_high'].mean() * 100
prt(f"\nA1 — Did price pull back below entry before making session high?")
prt(f"     {a1_pct:.1f}% of events")

# A2
pb = ext['a2_deepest_pullback_pct']
prt(f"\nA2 — Pullback depth distribution (from entry, before session high):")
prt(f"     Median pullback:             {pb.median()*100:+.2f}%")
prt(f"     Mean pullback:               {pb.mean()*100:+.2f}%")
prt(f"     10th pctl (shallow):         {pb.quantile(0.90)*100:+.2f}%")
prt(f"     90th pctl (deep):            {pb.quantile(0.10)*100:+.2f}%")

abs_pb = pb.abs() * 100
pb_buckets = [(0, 1, '0-1%'), (1, 2, '1-2%'), (2, 3, '2-3%'), (3, 5, '3-5%'), (5, 100, '5%+')]
prt(f"     Distribution:")
for lo, hi, label in pb_buckets:
    pct = ((abs_pb >= lo) & (abs_pb < hi)).mean() * 100
    prt(f"       {label}: {pct:.1f}%")

# A3
prt(f"\nA3 — Pullback timing:")
pb_min = ext['a3_pullback_minutes']
pb_bidx = ext['a3_pullback_bar_idx']
prt(f"     Median bar index of deepest pullback: {pb_bidx.median():.0f}")
prt(f"     Median minutes from entry:            {pb_min.median():.0f} min")
w30 = (pb_min <= 30).mean() * 100
w30_60 = ((pb_min > 30) & (pb_min <= 60)).mean() * 100
w60p = (pb_min > 60).mean() * 100
prt(f"     Within first 30 min after entry:  {w30:.1f}%")
prt(f"     Between 30-60 min after entry:    {w30_60:.1f}%")
prt(f"     After 60 min from entry:          {w60p:.1f}%")

# A4
a4_pct = ext['a4_recovered_above_ft_high'].mean() * 100
prt(f"\nA4 — After pullback, did price exceed FT bar's high?")
prt(f"     {a4_pct:.1f}% of events")

# ═══ SECTION B: SESSION HIGH BEHAVIOR ═══
prt("\n" + "=" * 70)
prt("═══ SECTION B: SESSION HIGH BEHAVIOR ═══")
prt("=" * 70)

# B1
dd = ext['b1_drawdown_from_session_high']
prt(f"\nB1 — Max drawdown from session high (before EOD close):")
prt(f"     Median:              {dd.median()*100:+.2f}%")
prt(f"     25th pctl:           {dd.quantile(0.25)*100:+.2f}%")
prt(f"     75th pctl:           {dd.quantile(0.75)*100:+.2f}%")
prt(f"     90th pctl (danger):  {dd.quantile(0.10)*100:+.2f}%")

abs_dd = dd.abs() * 100
dd_buckets = [(0, 1, '0-1%'), (1, 2, '1-2%'), (2, 3, '2-3%'),
              (3, 5, '3-5%'), (5, 7, '5-7%'), (7, 100, '7%+')]
prt(f"     Distribution:")
for lo, hi, label in dd_buckets:
    pct = ((abs_dd >= lo) & (abs_dd < hi)).mean() * 100
    prt(f"       {label}: {pct:.1f}%")

# B2
b2_pct = ext['b2_multiple_hod_attempts'].mean() * 100
prt(f"\nB2 — Multiple HoD attempts (touch, retreat >1%, return to high)?")
prt(f"     {b2_pct:.1f}% of events")

# B3
prt(f"\nB3 — HoD timing buckets:")
hod_m = ext['hod_minutes_from_open']
for label, lo, hi in HOD_BUCKETS:
    if label.startswith('Final'):
        pct = ((hod_m >= lo) & (hod_m <= hi)).mean() * 100
    else:
        pct = ((hod_m >= lo) & (hod_m < hi)).mean() * 100
    prt(f"     {label:>24s}: {pct:.1f}%")
prt(f"     Median HoD: {hod_m.median():.0f} min from open "
    f"({int(hod_m.median())//60}h {int(hod_m.median())%60}m)")

# ═══ SECTION C: ENTRY TIMING ANALYSIS ═══
prt("\n" + "=" * 70)
prt("═══ SECTION C: ENTRY TIMING ANALYSIS ═══")
prt("=" * 70)

e2_df = ext[ext['e2_found'] == True]
e3_df = ext[ext['e3_found'] == True]

prt(f"\nE1 — Breakout Entry (FT bar close): n={len(ext)}")
prt(f"     Win Rate:       {(ext['e1_eod_return'] > 0).mean()*100:.1f}%")
prt(f"     Avg EOD Return: {ext['e1_eod_return'].mean()*100:+.2f}%")
prt(f"     Median MAE:     {ext['e1_mae'].median()*100:+.2f}%")
prt(f"     Median MFE:     {ext['e1_mfe'].median()*100:+.2f}%")

prt(f"\nE2 — First Pullback Entry: n={len(e2_df)}")
if len(e2_df) > 0:
    prt(f"     Win Rate:       {(e2_df['e2_eod_return'] > 0).mean()*100:.1f}%")
    prt(f"     Avg EOD Return: {e2_df['e2_eod_return'].mean()*100:+.2f}%")
    prt(f"     Median MAE:     {e2_df['e2_mae'].median()*100:+.2f}%")
    prt(f"     Median MFE:     {e2_df['e2_mfe'].median()*100:+.2f}%")
    prt(f"     Avg price improvement vs E1: {e2_df['e2_price_improvement'].mean()*100:+.2f}%")
    prt(f"     % events cheaper than E1:    {e2_df['e2_cheaper'].mean()*100:.1f}%")

prt(f"\nE3 — Deepest Pullback Entry: n={len(e3_df)}")
if len(e3_df) > 0:
    prt(f"     Win Rate:       {(e3_df['e3_eod_return'] > 0).mean()*100:.1f}%")
    prt(f"     Avg EOD Return: {e3_df['e3_eod_return'].mean()*100:+.2f}%")
    prt(f"     Median MAE:     {e3_df['e3_mae'].median()*100:+.2f}%")
    prt(f"     Median MFE:     {e3_df['e3_mfe'].median()*100:+.2f}%")
    prt(f"     Avg price improvement vs E1: {e3_df['e3_price_improvement'].mean()*100:+.2f}%")
    prt(f"     % events cheaper than E1:    {e3_df['e3_cheaper'].mean()*100:.1f}%")

# ═══ SECTION D: HOLD TIME ANALYSIS ═══
prt("\n" + "=" * 70)
prt("═══ SECTION D: HOLD TIME ANALYSIS ═══")
prt("=" * 70)

# D1: For WINNING trades, % of MFE captured at each hold time
winners = ext[ext['e1_eod_return'] > 0]
prt(f"\nD1 — % of MFE captured at each exit time (winners only, n={len(winners)}):")
for label, _ in HOLD_TIMES_ET.items():
    safe = label.split(' ')[0].replace(':', '')
    col = f'hold_mfe_pct_{safe}'
    if col in winners.columns:
        avg_pct = winners[col].mean()
        prt(f"     Hold to {label}: {avg_pct:.1f}% of MFE captured")
# EOD as % of MFE
if len(winners) > 0:
    w_mfe = winners['full_mfe_pct']
    w_eod = winners['e1_eod_return']
    valid = w_mfe > 0
    if valid.any():
        eod_as_pct_mfe = (w_eod[valid] / w_mfe[valid] * 100)
        eod_as_pct_mfe = eod_as_pct_mfe.replace([np.inf, -np.inf], np.nan).dropna()
        prt(f"     Hold to EOD:                      {eod_as_pct_mfe.mean():.1f}% of MFE captured")

# D2: Early exit cost
prt(f"\nD2 — Early exit cost (all events, n={len(ext)}):")
avg_eod = ext['e1_eod_return'].mean()
for label, _ in HOLD_TIMES_ET.items():
    safe = label.split(' ')[0].replace(':', '')
    col = f'hold_return_{safe}'
    if col in ext.columns:
        avg_ret = ext[col].mean()
        if avg_eod != 0:
            pct_left = ((avg_eod - avg_ret) / abs(avg_eod)) * 100
        else:
            pct_left = 0
        prt(f"     Exit at {label}: avg return {avg_ret*100:+.2f}% "
            f"(leaves {pct_left:.1f}% of total return on table)")
prt(f"     Hold to EOD:                      avg return {avg_eod*100:+.2f}% (baseline)")

# D3: HoD timing by gap size bucket
prt(f"\nD3 — Median HoD timing by gap size bucket:")
for label, lo, hi in GAP_BUCKETS:
    bucket = ext[(ext['gap_pct'] >= lo) & (ext['gap_pct'] < hi)]
    if len(bucket) >= 5:
        med_hod = bucket['hod_minutes_from_open'].median()
        ct_time_hr = 8 + (30 + int(med_hod)) // 60
        ct_time_min = (30 + int(med_hod)) % 60
        prt(f"     {label:>6s} (n={len(bucket):>4d}): Median HoD at {med_hod:.0f} min "
            f"from open (~{ct_time_hr}:{ct_time_min:02d} CT)")

# ═══ SECTION E: R:R COMPARISON TABLE ═══
prt("\n" + "=" * 70)
prt("═══ SECTION E: R:R COMPARISON TABLE ═══")
prt("=" * 70)


def build_rr_table(df, table_label="ALL"):
    """Build a formatted R:R comparison table for E1/E2/E3."""
    e1_n = len(df)
    e1_wr = (df['e1_eod_return'] > 0).mean() * 100
    e1_avg = df['e1_eod_return'].mean() * 100
    e1_mae_med = df['e1_mae'].median() * 100
    e1_mfe_med = df['e1_mfe'].median() * 100
    e1_rr = abs(e1_mfe_med / e1_mae_med) if e1_mae_med != 0 else float('inf')

    e2 = df[df['e2_found'] == True]
    e2_n = len(e2)
    if e2_n > 0:
        e2_wr = (e2['e2_eod_return'] > 0).mean() * 100
        e2_avg = e2['e2_eod_return'].mean() * 100
        e2_mae_med = e2['e2_mae'].median() * 100
        e2_mfe_med = e2['e2_mfe'].median() * 100
        e2_rr = abs(e2_mfe_med / e2_mae_med) if e2_mae_med != 0 else float('inf')
        e2_price = e2['e2_price_improvement'].mean() * 100
        e2_cheap = e2['e2_cheaper'].mean() * 100
    else:
        e2_wr = e2_avg = e2_mae_med = e2_mfe_med = e2_rr = e2_price = e2_cheap = 0

    e3 = df[df['e3_found'] == True]
    e3_n = len(e3)
    if e3_n > 0:
        e3_wr = (e3['e3_eod_return'] > 0).mean() * 100
        e3_avg = e3['e3_eod_return'].mean() * 100
        e3_mae_med = e3['e3_mae'].median() * 100
        e3_mfe_med = e3['e3_mfe'].median() * 100
        e3_rr = abs(e3_mfe_med / e3_mae_med) if e3_mae_med != 0 else float('inf')
        e3_price = e3['e3_price_improvement'].mean() * 100
        e3_cheap = e3['e3_cheaper'].mean() * 100
    else:
        e3_wr = e3_avg = e3_mae_med = e3_mfe_med = e3_rr = e3_price = e3_cheap = 0

    lines = []
    lines.append(f"\n  ── {table_label} ──")
    hdr = f"  {'Metric':<28s} | {'E1 Breakout':>12s} | {'E2 First PB':>12s} | {'E3 Deep PB':>12s}"
    sep = f"  {'-'*28}-+-{'-'*12}-+-{'-'*12}-+-{'-'*12}"
    lines.append(hdr)
    lines.append(sep)
    lines.append(f"  {'Events with Entry':<28s} | {e1_n:>12d} | {e2_n:>12d} | {e3_n:>12d}")
    lines.append(f"  {'Win Rate':<28s} | {e1_wr:>11.1f}% | {e2_wr:>11.1f}% | {e3_wr:>11.1f}%")
    lines.append(f"  {'Avg EOD Return':<28s} | {e1_avg:>+11.2f}% | {e2_avg:>+11.2f}% | {e3_avg:>+11.2f}%")
    lines.append(f"  {'Median MAE %':<28s} | {e1_mae_med:>+11.2f}% | {e2_mae_med:>+11.2f}% | {e3_mae_med:>+11.2f}%")
    lines.append(f"  {'Median MFE %':<28s} | {e1_mfe_med:>+11.2f}% | {e2_mfe_med:>+11.2f}% | {e3_mfe_med:>+11.2f}%")
    lines.append(f"  {'Median R:R (MFE/MAE)':<28s} | {e1_rr:>11.2f}x | {e2_rr:>11.2f}x | {e3_rr:>11.2f}x")
    lines.append(f"  {'Avg Price vs E1':<28s} | {'baseline':>12s} | {e2_price:>+11.2f}% | {e3_price:>+11.2f}%")
    lines.append(f"  {'% Cheaper than E1':<28s} | {'N/A':>12s} | {e2_cheap:>11.1f}% | {e3_cheap:>11.1f}%")
    return lines


# Overall table
for line in build_rr_table(ext, "ALL EVENTS"):
    prt(line)

# By gap size bucket
for label, lo, hi in GAP_BUCKETS:
    bucket = ext[(ext['gap_pct'] >= lo) & (ext['gap_pct'] < hi)]
    if len(bucket) >= 10:
        for line in build_rr_table(bucket, f"Gap {label}"):
            prt(line)

## ═══════════════════════════════════════════════════════════════
## STEP 5: SAVE ALL RESULTS
## ═══════════════════════════════════════════════════════════════

prt("\n" + "=" * 70)
prt("═══ SAVING RESULTS ═══")
prt("=" * 70)

# 1. Extended event-level CSV
csv_path = os.path.join(OUTPUT_DIR, 'extended_analysis_results.csv')
ext.to_csv(csv_path, index=False)
prt(f"\n✅ {csv_path}")

# 2. Summary stats text
txt_path = os.path.join(OUTPUT_DIR, 'extended_summary_stats.txt')
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))
prt(f"✅ {txt_path}")

# 3. R:R comparison table CSV
rr_rows = []
for label, lo, hi in [('ALL', 0.0, 1.0)] + list(GAP_BUCKETS):
    if label == 'ALL':
        bucket = ext
    else:
        bucket = ext[(ext['gap_pct'] >= lo) & (ext['gap_pct'] < hi)]
    if len(bucket) < 5:
        continue
    for entry_label, prefix in [('E1_Breakout', 'e1'), ('E2_FirstPB', 'e2'), ('E3_DeepPB', 'e3')]:
        if prefix == 'e1':
            sub = bucket
        else:
            sub = bucket[bucket[f'{prefix}_found'] == True]
        n = len(sub)
        if n == 0:
            continue
        wr = (sub[f'{prefix}_eod_return'] > 0).mean() * 100
        avg_ret = sub[f'{prefix}_eod_return'].mean() * 100
        med_mae = sub[f'{prefix}_mae'].median() * 100
        med_mfe = sub[f'{prefix}_mfe'].median() * 100
        rr = abs(med_mfe / med_mae) if med_mae != 0 else 0
        rr_rows.append({
            'gap_bucket': label,
            'entry_type': entry_label,
            'n': n,
            'win_rate': round(wr, 1),
            'avg_eod_return': round(avg_ret, 2),
            'median_mae': round(med_mae, 2),
            'median_mfe': round(med_mfe, 2),
            'rr_ratio': round(rr, 2)
        })

rr_df = pd.DataFrame(rr_rows)
rr_csv_path = os.path.join(OUTPUT_DIR, 'rr_comparison_table.csv')
rr_df.to_csv(rr_csv_path, index=False)
prt(f"✅ {rr_csv_path}")

## ═══════════════════════════════════════════════════════════════
## FINAL SUMMARY
## ═══════════════════════════════════════════════════════════════

# Determine best entry by R:R
e1_rr_final = abs(ext['e1_mfe'].median() / ext['e1_mae'].median()) if ext['e1_mae'].median() != 0 else 0
e2_sub = ext[ext['e2_found'] == True]
e2_rr_final = abs(e2_sub['e2_mfe'].median() / e2_sub['e2_mae'].median()) \
    if len(e2_sub) > 0 and e2_sub['e2_mae'].median() != 0 else 0
e3_sub = ext[ext['e3_found'] == True]
e3_rr_final = abs(e3_sub['e3_mfe'].median() / e3_sub['e3_mae'].median()) \
    if len(e3_sub) > 0 and e3_sub['e3_mae'].median() != 0 else 0

best_rr_label = 'E1'
best_rr_val = e1_rr_final
if e2_rr_final > best_rr_val:
    best_rr_label = 'E2'
    best_rr_val = e2_rr_final
if e3_rr_final > best_rr_val:
    best_rr_label = 'E3'
    best_rr_val = e3_rr_final

e1_wr_final = (ext['e1_eod_return'] > 0).mean() * 100
e2_wr_final = (e2_sub['e2_eod_return'] > 0).mean() * 100 if len(e2_sub) > 0 else 0

# D2 early exit cost at 9:30 CT
col_930 = 'hold_return_930'
if col_930 in ext.columns:
    avg_930_ret = ext[col_930].mean() * 100
    avg_eod_ret = ext['e1_eod_return'].mean() * 100
    if avg_eod_ret != 0:
        exit_cost_930 = ((avg_eod_ret - avg_930_ret) / abs(avg_eod_ret)) * 100
    else:
        exit_cost_930 = 0
else:
    exit_cost_930 = 0

dd_med = ext['b1_drawdown_from_session_high'].median() * 100
total_time = time.time() - t0

prt("\n" + "=" * 70)
prt("=== EXTENDED STUDY COMPLETE ===")
prt(f"Events processed: {len(ext)} / {total_events}")
prt(f"Bug fix: OLD stat = {OLD_BUG_STAT:.1f}% → CORRECTED stat = {corrected_stat:.1f}%")
prt(f"Key finding A: Pullback before new high occurs in {a1_pct:.1f}% of events")
prt(f"Key finding B: Median pullback from session high = {dd_med:+.2f}%")
prt(f"Key finding C: E2 win rate vs E1 win rate = {e2_wr_final:.1f}% vs {e1_wr_final:.1f}%")
prt(f"Key finding D: Exiting at 9:30 CT leaves {exit_cost_930:.1f}% of return on table")
prt(f"Best entry by R:R: {best_rr_label} ({best_rr_val:.2f}x)")
prt(f"Total runtime: {total_time:.0f}s ({total_time/60:.1f} min)")
prt("=" * 70)

# Re-save summary with final lines
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

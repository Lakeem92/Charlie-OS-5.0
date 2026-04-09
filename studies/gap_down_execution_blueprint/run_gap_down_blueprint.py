"""
Gap-Down Execution Blueprint — Base Study (V1)
Mirror of gap_execution_blueprint for SHORT side.

Scans for gap-downs >= 2%, bearish/neutral first candle with
downside follow-through, then computes session metrics from
the short entry perspective.
"""

import sys, os, time
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')

from shared.data_router import DataRouter
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

OUTPUT_DIR = r'C:\QuantLab\Data_Lab\studies\gap_down_execution_blueprint\outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

WATCHLIST_PATH = r'C:\QuantLab\Data_Lab\shared\config\watchlist.csv'

START_DATE = '2024-01-01'
END_DATE   = '2026-03-06'
GAP_THRESHOLD = -0.02          # <= -2% gap-down
ATR_PERIOD = 14
FT_ATR_MULT = 0.40             # follow-through = Close <= Open - (ATR * 0.40)
BODY_RATIO_THRESHOLD = 0.40    # candle body > 40% of range = directional
CHUNK_DAYS = 120
SESSION_OPEN_ET  = "09:30"
SESSION_CLOSE_ET = "16:00"

# ═══════════════════════════════════════════════════════════════
# STEP 1: LOAD WATCHLIST
# ═══════════════════════════════════════════════════════════════

t0 = time.time()
print("=" * 70)
print("GAP-DOWN EXECUTION BLUEPRINT — BASE STUDY")
print("=" * 70)

wl = pd.read_csv(WATCHLIST_PATH)
if 'symbol' in wl.columns:
    tickers = sorted(wl['symbol'].dropna().unique().tolist())
elif 'ticker' in wl.columns:
    tickers = sorted(wl['ticker'].dropna().unique().tolist())
else:
    tickers = sorted(wl.iloc[:, 0].dropna().unique().tolist())

print(f"Loaded {len(tickers)} tickers from watchlist")

# ═══════════════════════════════════════════════════════════════
# STEP 2: SCAN FOR GAP-DOWN EVENTS + COMPUTE ATR
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 2: Scanning for gap-down events (<= -2%)")
print("=" * 70)

all_gap_events = []
api_ok = 0
api_fail = 0

for i, ticker in enumerate(tickers):
    if (i + 1) % 25 == 0 or (i + 1) == len(tickers):
        print(f"  Scanning {i+1}/{len(tickers)} tickers... "
              f"({len(all_gap_events)} gaps found)")

    try:
        daily = DataRouter.get_price_data(
            ticker, START_DATE, end_date=END_DATE,
            timeframe='daily'
        )
        if daily is None or len(daily) < ATR_PERIOD + 5:
            api_fail += 1
            continue
        api_ok += 1

        daily = daily.sort_index()

        # Compute ATR14
        high = daily['High']
        low = daily['Low']
        close = daily['Close']
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        daily['atr'] = tr.rolling(ATR_PERIOD).mean()

        # Find gap-downs
        daily['prev_close'] = close.shift(1)
        daily['gap_pct'] = (daily['Open'] - daily['prev_close']) / daily['prev_close']

        for idx_dt, row in daily.iterrows():
            if pd.isna(row['gap_pct']) or pd.isna(row['atr']):
                continue
            if row['gap_pct'] > GAP_THRESHOLD:  # not a gap-down <= -2%
                continue
            if row['atr'] <= 0:
                continue

            # Follow-through level: Open - (ATR * 0.40)
            ft_level = row['Open'] - (row['atr'] * FT_ATR_MULT)

            dt = pd.Timestamp(idx_dt)
            all_gap_events.append({
                'ticker': ticker,
                'date': dt.strftime('%Y-%m-%d'),
                'open_price': row['Open'],
                'prev_close': row['prev_close'],
                'gap_pct': round(row['gap_pct'], 6),
                'atr': round(row['atr'], 4),
                'follow_through_level': round(ft_level, 4),
                'daily_high': row['High'],
                'daily_low': row['Low'],
                'daily_close': row['Close'],
            })

    except Exception:
        api_fail += 1
        continue

gap_df = pd.DataFrame(all_gap_events)
print(f"\nTotal gap-down events found: {len(gap_df)}")
print(f"API calls: {api_ok} ok, {api_fail} fail")

# Save gap cache
gap_cache_path = os.path.join(OUTPUT_DIR, 'gap_down_events_cache.csv')
gap_df.to_csv(gap_cache_path, index=False)
print(f"Saved: {gap_cache_path}")

# ═══════════════════════════════════════════════════════════════
# STEP 3: CLASSIFY FIRST CANDLE + CHECK FOLLOW-THROUGH (5-min)
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 3: Classifying first candle + checking downside follow-through")
print("=" * 70)

# Group events by ticker for efficient API calls
events_by_ticker = defaultdict(list)
for _, ev in gap_df.iterrows():
    events_by_ticker[ev['ticker']].append(ev)

classified_events = []
no_intraday = 0
bearish_count = 0     # bearish = good for gap-down (continuation)
neutral_count = 0
bullish_excluded = 0  # bullish = excluded (against the gap direction)
ft_confirmed = 0
ft_failed = 0

t2 = time.time()
chunk_count = 0

for ti, (ticker, events) in enumerate(sorted(events_by_ticker.items())):
    if (ti + 1) % 25 == 0 or (ti + 1) == len(events_by_ticker):
        elapsed = time.time() - t2
        print(f"  Ticker {ti+1}/{len(events_by_ticker)} | "
              f"{len(classified_events)} classified | "
              f"{chunk_count} API chunks | {elapsed:.0f}s")

    event_dates = [pd.Timestamp(e['date']) for e in events]
    min_dt = min(event_dates) - timedelta(days=1)
    max_dt = max(event_dates) + timedelta(days=1)

    # Fetch intraday in chunks
    chunks = []
    cursor = min_dt
    while cursor <= max_dt:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), max_dt)
        chunks.append((cursor.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        cursor = chunk_end + timedelta(days=1)

    ticker_frames = []
    for start_str, end_str in chunks:
        chunk_count += 1
        try:
            intraday = DataRouter.get_price_data(
                ticker, start_str, end_date=end_str,
                timeframe='5min', fallback=False
            )
            if intraday is not None and len(intraday) > 0:
                intraday = intraday.sort_index()
                if isinstance(intraday.index, pd.DatetimeIndex) and intraday.index.tz is not None:
                    intraday.index = intraday.index.tz_convert('US/Eastern')
                ticker_frames.append(intraday)
        except Exception:
            continue

    if not ticker_frames:
        no_intraday += len(events)
        continue

    combined = pd.concat(ticker_frames).sort_index()
    combined = combined[~combined.index.duplicated(keep='last')]

    for ev in events:
        try:
            event_date = pd.Timestamp(ev['date'])
            day_bars = combined[combined.index.date == event_date.date()]
            session = day_bars.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)

            if len(session) < 10:
                no_intraday += 1
                continue

            first_bar = session.iloc[0]
            fb_open = first_bar['Open']
            fb_close = first_bar['Close']
            fb_high = first_bar['High']
            fb_low = first_bar['Low']
            fb_range = fb_high - fb_low

            # Classify first candle
            if fb_range == 0:
                candle_color = 'NEUTRAL'
            else:
                body = abs(fb_close - fb_open)
                body_ratio = body / fb_range

                if body_ratio <= BODY_RATIO_THRESHOLD:
                    candle_color = 'NEUTRAL'
                elif fb_close < fb_open:
                    candle_color = 'BEARISH'    # good for gap-down
                else:
                    candle_color = 'BULLISH'    # bad — exclude

            if candle_color == 'BULLISH':
                bullish_excluded += 1
                continue
            elif candle_color == 'BEARISH':
                bearish_count += 1
            else:
                neutral_count += 1

            # Check for downside follow-through
            # FT = first 5-min bar where Close <= follow_through_level
            ft_level = ev['follow_through_level']
            ft_bar_idx = None
            for j in range(len(session)):
                if session.iloc[j]['Close'] <= ft_level:
                    ft_bar_idx = j
                    break

            if ft_bar_idx is None:
                ft_failed += 1
                continue

            ft_confirmed += 1

            ft_bar = session.iloc[ft_bar_idx]
            entry_price = ft_bar['Close']       # short entry
            entry_time = session.index[ft_bar_idx]
            session_open_time = session.index[0]

            # Bars from entry onward
            from_entry = session.iloc[ft_bar_idx:]
            after_entry = session.iloc[ft_bar_idx + 1:] if ft_bar_idx + 1 < len(session) else pd.DataFrame()
            eod_close = session.iloc[-1]['Close']

            # SHORT perspective metrics
            # MAE = highest high after entry (worst for a short)
            # MFE = lowest low after entry (best for a short)
            mae_price = from_entry['High'].max()
            mfe_price = from_entry['Low'].min()

            mae_pct = (mae_price - entry_price) / entry_price   # positive = bad for short
            mfe_pct = (entry_price - mfe_price) / entry_price   # positive = good for short

            # EOD return for SHORT: (entry - eod_close) / entry
            eod_return = (entry_price - eod_close) / entry_price

            # Did price go ABOVE entry after FT? (adverse for short)
            price_above_entry_after_ft = False
            if len(after_entry) > 0:
                price_above_entry_after_ft = bool(
                    (after_entry['High'] > entry_price).any()
                )

            # LoD timing (the money destination for shorts)
            session_low_price = session['Low'].min()
            session_low_idx = session['Low'].idxmin()
            lod_minutes_from_open = (
                (session_low_idx - session_open_time).total_seconds() / 60.0
            )

            # HoD timing (the bounce / danger)
            session_high_price = session['High'].max()
            session_high_idx = session['High'].idxmax()
            hod_minutes_from_open = (
                (session_high_idx - session_open_time).total_seconds() / 60.0
            )

            # FT bar timing
            ft_minutes_from_open = (
                (entry_time - session_open_time).total_seconds() / 60.0
            )

            # Bounce above entry before LoD (pullback against short before continuation)
            bounce_above_entry_before_lod = False
            if len(after_entry) > 0:
                post_entry_low_idx = after_entry['Low'].idxmin()
                bars_before_low = after_entry[after_entry.index <= post_entry_low_idx]
                if len(bars_before_low) > 0:
                    if (bars_before_low['High'] > entry_price).any():
                        bounce_above_entry_before_lod = True

            # Pullback depth before new low (bounce price vs entry)
            bounce_depth_before_lod = 0.0
            if len(after_entry) > 0:
                post_entry_low_idx = after_entry['Low'].idxmin()
                bars_before_low = after_entry[after_entry.index <= post_entry_low_idx]
                if len(bars_before_low) > 0:
                    max_bounce = bars_before_low['High'].max()
                    bounce_depth_before_lod = (max_bounce - entry_price) / entry_price

            classified_events.append({
                'ticker': ticker,
                'date': ev['date'],
                'gap_pct': ev['gap_pct'],
                'atr': ev['atr'],
                'candle_color': candle_color,
                'follow_through_level': ft_level,
                'ft_bar_idx': ft_bar_idx,
                'ft_minutes_from_open': round(ft_minutes_from_open, 1),
                'entry_price': round(entry_price, 4),
                'eod_close': round(eod_close, 4),
                'eod_return': round(eod_return, 6),
                'mae_pct': round(mae_pct, 6),      # positive = bad (bounce against short)
                'mfe_pct': round(mfe_pct, 6),      # positive = good (further drop)
                'mae_price': round(mae_price, 4),
                'mfe_price': round(mfe_price, 4),
                'price_above_entry_after_ft': price_above_entry_after_ft,
                'bounce_above_entry_before_lod': bounce_above_entry_before_lod,
                'bounce_depth_before_lod': round(bounce_depth_before_lod, 6),
                'session_low_price': round(session_low_price, 4),
                'session_high_price': round(session_high_price, 4),
                'lod_minutes_from_open': round(lod_minutes_from_open, 1),
                'hod_minutes_from_open': round(hod_minutes_from_open, 1),
            })

        except Exception:
            no_intraday += 1
            continue

results_df = pd.DataFrame(classified_events)

print(f"\n{'='*50}")
print(f"CLASSIFICATION SUMMARY")
print(f"{'='*50}")
print(f"Total gap-down events scanned:  {len(gap_df)}")
print(f"Bullish opens (excluded):       {bullish_excluded}")
print(f"No follow-through (excluded):   {ft_failed}")
print(f"No intraday data:               {no_intraday}")
print(f"Bearish first candle:           {bearish_count}")
print(f"Neutral first candle:           {neutral_count}")
print(f"Follow-through confirmed:       {ft_confirmed}")
print(f"Included in analysis:           {len(results_df)}")

# Save classified events
classified_path = os.path.join(OUTPUT_DIR, 'gap_down_classified_events.csv')
results_df.to_csv(classified_path, index=False)
print(f"\nSaved: {classified_path}")

# Save included events
events_path = os.path.join(OUTPUT_DIR, 'gap_down_blueprint_events.csv')
results_df.to_csv(events_path, index=False)
print(f"Saved: {events_path}")

if len(results_df) == 0:
    print("\n⚠️  No events passed all filters. Check data availability.")
    sys.exit(0)

# ═══════════════════════════════════════════════════════════════
# STEP 4: BASE STUDY RESULTS (V1 FINDINGS)
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 4: BASE STUDY RESULTS")
print("=" * 70)

output_lines = []


def prt(line=""):
    print(line)
    output_lines.append(line)


n = len(results_df)
gap_abs = results_df['gap_pct'].abs()

prt(f"\nTotal included events: {n}")
prt(f"Unique tickers: {results_df['ticker'].nunique()}")

# ── Finding 1: Candle Color ──
prt(f"\n{'='*60}")
prt("FINDING 1: CANDLE COLOR — BEARISH vs NEUTRAL (Short Side)")
prt(f"{'='*60}")

for color in ['BEARISH', 'NEUTRAL']:
    sub = results_df[results_df['candle_color'] == color]
    if len(sub) == 0:
        continue
    wr = (sub['eod_return'] > 0).mean() * 100
    avg_ret = sub['eod_return'].mean() * 100
    med_ret = sub['eod_return'].median() * 100
    avg_winner = sub[sub['eod_return'] > 0]['eod_return'].mean() * 100 if (sub['eod_return'] > 0).any() else 0
    avg_loser = sub[sub['eod_return'] <= 0]['eod_return'].mean() * 100 if (sub['eod_return'] <= 0).any() else 0
    prt(f"\n  {color} (n={len(sub)}):")
    prt(f"    EOD Win Rate (short):  {wr:.1f}%")
    prt(f"    Avg EOD Return:        {avg_ret:+.2f}%")
    prt(f"    Median EOD Return:     {med_ret:+.2f}%")
    prt(f"    Avg Winner:            {avg_winner:+.2f}%")
    prt(f"    Avg Loser:             {avg_loser:+.2f}%")

combined_wr = (results_df['eod_return'] > 0).mean() * 100
combined_avg = results_df['eod_return'].mean() * 100
combined_med = results_df['eod_return'].median() * 100
prt(f"\n  COMBINED (n={n}):")
prt(f"    EOD Win Rate (short):  {combined_wr:.1f}%")
prt(f"    Avg EOD Return:        {combined_avg:+.2f}%")
prt(f"    Median EOD Return:     {combined_med:+.2f}%")

# ── Finding 2: LoD Timing ──
prt(f"\n{'='*60}")
prt("FINDING 2: LOW OF DAY TIMING (when does the bottom get set?)")
prt(f"{'='*60}")

lod = results_df['lod_minutes_from_open']
prt(f"\n  Median LoD: {lod.median():.0f} min from open "
    f"({int(lod.median())//60}h {int(lod.median())%60}m)")
prt(f"  Mean LoD:   {lod.mean():.0f} min from open "
    f"({int(lod.mean())//60}h {int(lod.mean())%60}m)")
prt(f"  LoD in first 5 min:    {(lod <= 5).mean()*100:.1f}%")
prt(f"  LoD in first 15 min:   {(lod <= 15).mean()*100:.1f}%")
prt(f"  LoD in first 30 min:   {(lod <= 30).mean()*100:.1f}%")
prt(f"  LoD in first 60 min:   {(lod <= 60).mean()*100:.1f}%")
prt(f"  LoD in first 2 hours:  {(lod <= 120).mean()*100:.1f}%")
prt(f"  LoD in last hour:      {(lod >= 330).mean()*100:.1f}%")

# CT translation
lod_ct_mins = lod.median() - 60  # ET to CT
prt(f"\n  CT translation: Median LoD at ~{8 + int((30 + lod.median())//60)}:"
    f"{int((30 + lod.median())%60):02d} ET = "
    f"~{8 + int((30 + lod.median())//60) - 1}:"
    f"{int((30 + lod.median())%60):02d} CT")

# ── Finding 3: HoD Timing (the bounce) ──
prt(f"\n{'='*60}")
prt("FINDING 3: HIGH OF DAY TIMING (the bounce / worst case for shorts)")
prt(f"{'='*60}")

hod = results_df['hod_minutes_from_open']
prt(f"\n  Median HoD: {hod.median():.0f} min from open "
    f"({int(hod.median())//60}h {int(hod.median())%60}m)")
prt(f"  Mean HoD:   {hod.mean():.0f} min from open "
    f"({int(hod.mean())//60}h {int(hod.mean())%60}m)")
prt(f"  HoD in first 5 min:    {(hod <= 5).mean()*100:.1f}%")
prt(f"  HoD in first 30 min:   {(hod <= 30).mean()*100:.1f}%")
prt(f"  HoD in first 60 min:   {(hod <= 60).mean()*100:.1f}%")
prt(f"  HoD in last hour:      {(hod >= 330).mean()*100:.1f}%")

# ── Finding 4: P&L Profile ──
prt(f"\n{'='*60}")
prt("FINDING 4: P&L PROFILE (SHORT perspective)")
prt(f"{'='*60}")

mae = results_df['mae_pct']
mfe = results_df['mfe_pct']
prt(f"\n  MAE = worst bounce against short (positive = bad)")
prt(f"  Median MAE:     +{mae.median()*100:.2f}%")
prt(f"  Mean MAE:       +{mae.mean()*100:.2f}%")
prt(f"  Worst 10% MAE:  +{mae.quantile(0.90)*100:.2f}%")
prt(f"\n  MFE = best drop in your favor (positive = good)")
prt(f"  Median MFE:     +{mfe.median()*100:.2f}%")
prt(f"  Mean MFE:       +{mfe.mean()*100:.2f}%")
prt(f"  Best 10% MFE:   +{mfe.quantile(0.90)*100:.2f}%")

above_entry = results_df['price_above_entry_after_ft'].mean() * 100
prt(f"\n  Price above entry after FT:  {above_entry:.1f}%")
prt(f"  (% of shorts that see a bounce above their entry)")

bounce_before = results_df['bounce_above_entry_before_lod'].mean() * 100
prt(f"  Bounce above entry BEFORE LoD: {bounce_before:.1f}%")

bounce_depth = results_df['bounce_depth_before_lod']
prt(f"\n  Bounce depth before LoD (how far price goes against you before continuing down):")
prt(f"  Median: +{bounce_depth.median()*100:.2f}%")
prt(f"  Mean:   +{bounce_depth.mean()*100:.2f}%")
prt(f"  90th pct: +{bounce_depth.quantile(0.90)*100:.2f}%")

# R:R
avg_winner_all = results_df[results_df['eod_return'] > 0]['eod_return'].mean() * 100 if (results_df['eod_return'] > 0).any() else 0
avg_loser_all = results_df[results_df['eod_return'] <= 0]['eod_return'].mean() * 100 if (results_df['eod_return'] <= 0).any() else 0
rr = abs(avg_winner_all / avg_loser_all) if avg_loser_all != 0 else 0
prt(f"\n  Avg Winner (short): +{avg_winner_all:.2f}%")
prt(f"  Avg Loser (short):  {avg_loser_all:+.2f}%")
prt(f"  R:R Ratio:          {rr:.2f}:1")

# ── Finding 5: Gap Size Buckets ──
prt(f"\n{'='*60}")
prt("FINDING 5: GAP SIZE BUCKETS (SHORT perspective, absolute gap size)")
prt(f"{'='*60}")

gap_buckets = [
    ('2-3%',   0.02, 0.03),
    ('3-5%',   0.03, 0.05),
    ('5-8%',   0.05, 0.08),
    ('8-12%',  0.08, 0.12),
    ('12-20%', 0.12, 0.20),
    ('20%+',   0.20, 1.00),
]

prt(f"\n  {'Gap Down':<10s} {'n':>5s} {'WR':>7s} {'Avg Ret':>9s} "
    f"{'Med MAE':>9s} {'Med MFE':>9s} {'LoD<30m':>8s} {'MedLoD':>8s}")
prt(f"  {'-'*10} {'-'*5} {'-'*7} {'-'*9} {'-'*9} {'-'*9} {'-'*8} {'-'*8}")

for label, lo, hi in gap_buckets:
    bucket = results_df[(gap_abs >= lo) & (gap_abs < hi)]
    if len(bucket) < 5:
        prt(f"  {label:<10s} {len(bucket):>5d}   (too few events)")
        continue
    wr = (bucket['eod_return'] > 0).mean() * 100
    avg_ret = bucket['eod_return'].mean() * 100
    med_mae = bucket['mae_pct'].median() * 100
    med_mfe = bucket['mfe_pct'].median() * 100
    lod30 = (bucket['lod_minutes_from_open'] <= 30).mean() * 100
    med_lod = bucket['lod_minutes_from_open'].median()
    prt(f"  {label:<10s} {len(bucket):>5d} {wr:>6.1f}% {avg_ret:>+8.2f}% "
        f" +{med_mae:>7.2f}%  +{med_mfe:>7.2f}% {lod30:>7.1f}% {med_lod:>7.0f}m")

# ── V-Bottom Detection ──
prt(f"\n{'='*60}")
prt("FINDING 6: V-BOTTOM / MEAN-REVERSION DETECTION")
prt(f"{'='*60}")

# How many gap-down events close ABOVE the open? (full reversal)
close_above_open = (results_df['eod_close'] > results_df['entry_price'] * (1 + 0.005)).mean() * 100
close_above_open_1pct = (results_df['eod_close'] > results_df['entry_price'] * (1 + 0.01)).mean() * 100
prt(f"\n  Close >0.5% ABOVE entry (V-bottom):  {close_above_open:.1f}%")
prt(f"  Close >1.0% ABOVE entry (strong V):   {close_above_open_1pct:.1f}%")

# LoD in first 30 min AND close above entry = classic V-bottom
early_lod = results_df[results_df['lod_minutes_from_open'] <= 30]
if len(early_lod) > 0:
    v_bottoms = (early_lod['eod_return'] < -0.005).mean() * 100  # short lost >0.5%
    prt(f"\n  When LoD < 30 min (n={len(early_lod)}):")
    prt(f"    Short LOSES >0.5% by EOD:  {v_bottoms:.1f}%  (V-bottom rate)")

# LoD in last 2 hours = continuation
late_lod = results_df[results_df['lod_minutes_from_open'] >= 240]
if len(late_lod) > 0:
    late_wr = (late_lod['eod_return'] > 0).mean() * 100
    prt(f"\n  When LoD > 4 hours from open (n={len(late_lod)}):")
    prt(f"    Short win rate:             {late_wr:.1f}%  (continuation rate)")

# Save summary
summary_path = os.path.join(OUTPUT_DIR, 'base_study_summary.txt')
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))
prt(f"\nSaved: {summary_path}")

# ═══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════

total_time = time.time() - t0
prt(f"\n{'='*70}")
prt(f"=== GAP-DOWN BASE STUDY COMPLETE ===")
prt(f"Events included:            {n}")
prt(f"Unique tickers:             {results_df['ticker'].nunique()}")
prt(f"EOD Win Rate (short):       {combined_wr:.1f}%")
prt(f"Avg EOD Return (short):     {combined_avg:+.2f}%")
prt(f"Median EOD Return (short):  {combined_med:+.2f}%")
prt(f"Price bounces above entry:  {above_entry:.1f}%")
prt(f"Median LoD:                 {lod.median():.0f} min from open")
prt(f"Median HoD:                 {hod.median():.0f} min from open")
prt(f"API chunks:                 {chunk_count}")
prt(f"Runtime:                    {total_time:.0f}s ({total_time/60:.1f} min)")
prt(f"{'='*70}")

# Re-save with final lines
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"\nDone. All outputs in: {OUTPUT_DIR}")

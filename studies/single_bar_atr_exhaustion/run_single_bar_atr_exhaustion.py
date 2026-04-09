"""
Single-Bar ATR Exhaustion Study
===============================================================================
On a 5-minute chart, when a single bar consumes a large % of the daily ATR,
how often does the NEXT bar (or next 3/6 bars) pull back — and by how much?

Buckets:
  NORMAL      < 40 %
  HOT         40-60 %
  WARNING     60-80 %
  EXHAUSTION  80-100 %
  EXTREME     100 %+

Splits every bucket by long context (close > day open) vs short context.
Outputs summary tables + HTML bar chart.
"""

import sys, os, time
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\indicators')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')

from shared.data_router import DataRouter
from shared.chart_builder import ChartBuilder

import pandas as pd
import numpy as np
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

OUTPUT_DIR = r'C:\QuantLab\Data_Lab\studies\single_bar_atr_exhaustion\outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

WATCHLIST_PATH = r'C:\QuantLab\Data_Lab\shared\config\watchlist.csv'

START_DATE = '2024-01-01'
END_DATE   = '2026-03-06'
ATR_PERIOD = 14
CHUNK_DAYS = 120          # days per intraday API chunk
SESSION_OPEN_ET  = "09:30"
SESSION_CLOSE_ET = "16:00"
FORWARD_BARS = [1, 3, 6]  # how many bars ahead to measure

BUCKET_LABELS = ['NORMAL', 'HOT', 'WARNING', 'EXHAUSTION', 'EXTREME']
BUCKET_EDGES  = [0, 40, 60, 80, 100, float('inf')]  # percentages


def bucket_label(pct: float) -> str:
    """Map single_bar_pct to a bucket name."""
    if pct < 40:
        return 'NORMAL'
    elif pct < 60:
        return 'HOT'
    elif pct < 80:
        return 'WARNING'
    elif pct < 100:
        return 'EXHAUSTION'
    else:
        return 'EXTREME'


# ═══════════════════════════════════════════════════════════════
# STEP 1 — LOAD WATCHLIST
# ═══════════════════════════════════════════════════════════════

t0 = time.time()
print("=" * 72)
print("SINGLE-BAR ATR EXHAUSTION STUDY")
print("=" * 72)

wl = pd.read_csv(WATCHLIST_PATH)
tickers = sorted(wl['Symbol'].dropna().unique().tolist())
print(f"Loaded {len(tickers)} tickers from watchlist")
print(f"Period: {START_DATE} → {END_DATE}")
print(f"Forward measurement bars: {FORWARD_BARS}")
print()

# ═══════════════════════════════════════════════════════════════
# STEP 2 — FOR EACH TICKER: DAILY ATR + 5-MIN BARS
# ═══════════════════════════════════════════════════════════════

print("=" * 72)
print("STEP 2: Fetching daily + 5-min data, computing ATR consumption")
print("=" * 72)

# Write rows incrementally to CSV to avoid OOM on 3M+ rows
RAW_PATH = os.path.join(OUTPUT_DIR, 'raw_bar_data.csv')
# Remove stale file from prior run (we append)
if os.path.exists(RAW_PATH):
    os.remove(RAW_PATH)
CSV_COLUMNS = [
    'ticker', 'datetime', 'date', 'bar_range', 'daily_atr',
    'single_bar_pct', 'bucket', 'context',
    'pb_any_1', 'pb_depth_1', 'recovered_1', 'continuation_1',
    'pb_any_3', 'pb_depth_3', 'recovered_3', 'continuation_3',
    'pb_any_6', 'pb_depth_6', 'recovered_6', 'continuation_6',
    'recover_within_6',
]
_wrote_header = False
total_rows_written = 0
api_ok = 0
api_fail = 0
tickers_processed = 0

for ti, ticker in enumerate(tickers):
    if (ti + 1) % 10 == 0 or (ti + 1) == len(tickers) or (ti + 1) <= 3:
        elapsed = time.time() - t0
        print(f"  [{ti+1}/{len(tickers)}] {ticker:6s} | "
              f"{total_rows_written:,} bars written | {elapsed:.0f}s")

    # ── 2a: fetch daily data & compute Wilder ATR ────────────────
    try:
        daily = DataRouter.get_price_data(
            ticker, START_DATE, end_date=END_DATE, timeframe='daily'
        )
        if daily is None or len(daily) < ATR_PERIOD + 5:
            api_fail += 1
            continue
    except Exception:
        api_fail += 1
        continue

    daily = daily.sort_index()

    # True Range
    high  = daily['High']
    low   = daily['Low']
    close = daily['Close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)

    # Wilder's smoothing  (EWM with alpha = 1/period)
    daily['atr'] = tr.ewm(alpha=1.0 / ATR_PERIOD, min_periods=ATR_PERIOD, adjust=False).mean()

    # Build lookup: date → (ATR_for_that_day, day_open)
    # Use *prior day's* ATR as the baseline for today's bars
    daily['prior_atr'] = daily['atr'].shift(1)
    day_info = {}
    for idx, row in daily.iterrows():
        dt = pd.Timestamp(idx).date()
        if pd.notna(row['prior_atr']) and row['prior_atr'] > 0:
            day_info[dt] = {
                'atr': row['prior_atr'],
                'day_open': row['Open'],
            }

    if not day_info:
        api_fail += 1
        continue

    api_ok += 1

    # ── 2b: fetch 5-min intraday in chunks ───────────────────────
    min_dt = pd.Timestamp(START_DATE)
    max_dt = pd.Timestamp(END_DATE)

    chunks = []
    cursor = min_dt
    while cursor <= max_dt:
        chunk_end = min(cursor + pd.Timedelta(days=CHUNK_DAYS), max_dt)
        chunks.append((cursor.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        cursor = chunk_end + pd.Timedelta(days=1)

    intra_frames = []
    for s_str, e_str in chunks:
        try:
            intra = DataRouter.get_price_data(
                ticker, s_str, end_date=e_str,
                timeframe='5min', fallback=False
            )
            if intra is not None and len(intra) > 0:
                intra = intra.sort_index()
                if isinstance(intra.index, pd.DatetimeIndex) and intra.index.tz is not None:
                    intra.index = intra.index.tz_convert('US/Eastern')
                intra_frames.append(intra)
        except Exception:
            continue

    if not intra_frames:
        continue

    combined = pd.concat(intra_frames).sort_index()
    combined = combined[~combined.index.duplicated(keep='last')]

    # Filter to RTH
    combined = combined.between_time(SESSION_OPEN_ET, SESSION_CLOSE_ET)
    if len(combined) == 0:
        continue

    combined['date'] = combined.index.date

    # ── 2c: compute single-bar ATR consumption ───────────────────
    ticker_rows = []
    for dt_date, group in combined.groupby('date'):
        info = day_info.get(dt_date)
        if info is None:
            continue

        daily_atr = info['atr']
        day_open  = info['day_open']
        bars = group.sort_index()

        for bar_pos in range(len(bars)):
            bar = bars.iloc[bar_pos]
            bar_range = bar['High'] - bar['Low']
            if bar_range <= 0:
                continue
            single_bar_pct = (bar_range / daily_atr) * 100.0

            # Context: did bar close above or below day open?
            bar_close = bar['Close']
            context = 'LONG' if bar_close > day_open else 'SHORT'

            # ── forward bar metrics ──────────────────────────────
            fwd_data = {}
            max_fwd = max(FORWARD_BARS)

            for n in FORWARD_BARS:
                end_pos = bar_pos + n
                if end_pos >= len(bars):
                    # not enough forward bars left
                    fwd_data[f'pb_any_{n}']      = np.nan
                    fwd_data[f'pb_depth_{n}']    = np.nan
                    fwd_data[f'recovered_{n}']   = np.nan
                    fwd_data[f'continuation_{n}'] = np.nan
                    continue

                fwd_slice = bars.iloc[bar_pos + 1 : bar_pos + 1 + n]

                if context == 'LONG':
                    # pullback from this bar's high
                    ref_high  = bar['High']
                    ref_close = bar['Close']
                    fwd_lows  = fwd_slice['Low'].values
                    deepest_pullback = (ref_high - fwd_lows.min()) / daily_atr * 100.0
                    any_pullback = 1 if fwd_lows.min() < ref_close else 0
                    # recovered = fwd close > bar close
                    fwd_last_close = fwd_slice.iloc[-1]['Close']
                    recovered = 1 if fwd_last_close > ref_close else 0
                    # continuation = fwd highs exceeded bar high
                    fwd_highs = fwd_slice['High'].values
                    continuation = 1 if fwd_highs.max() > ref_high else 0
                else:
                    # short context: pullback from this bar's low
                    ref_low   = bar['Low']
                    ref_close = bar['Close']
                    fwd_highs = fwd_slice['High'].values
                    deepest_pullback = (fwd_highs.max() - ref_low) / daily_atr * 100.0
                    any_pullback = 1 if fwd_highs.max() > ref_close else 0
                    # recovered = fwd close < bar close
                    fwd_last_close = fwd_slice.iloc[-1]['Close']
                    recovered = 1 if fwd_last_close < ref_close else 0
                    # continuation = fwd lows broke below bar low
                    fwd_lows = fwd_slice['Low'].values
                    continuation = 1 if fwd_lows.min() < ref_low else 0

                fwd_data[f'pb_any_{n}']      = any_pullback
                fwd_data[f'pb_depth_{n}']    = deepest_pullback
                fwd_data[f'recovered_{n}']   = recovered
                fwd_data[f'continuation_{n}'] = continuation

            # Check for 6-bar recovery (using max forward window)
            rec_n = max(FORWARD_BARS)
            end_pos_rec = bar_pos + rec_n
            if end_pos_rec < len(bars):
                rec_slice = bars.iloc[bar_pos + 1 : bar_pos + 1 + rec_n]
                if context == 'LONG':
                    fwd_data['recover_within_6'] = 1 if (rec_slice['Close'] > bar['Close']).any() else 0
                else:
                    fwd_data['recover_within_6'] = 1 if (rec_slice['Close'] < bar['Close']).any() else 0
            else:
                fwd_data['recover_within_6'] = np.nan

            ticker_rows.append({
                'ticker': ticker,
                'datetime': str(bars.index[bar_pos]),
                'date': str(dt_date),
                'bar_range': round(bar_range, 4),
                'daily_atr': round(daily_atr, 4),
                'single_bar_pct': round(single_bar_pct, 2),
                'bucket': bucket_label(single_bar_pct),
                'context': context,
                **fwd_data,
            })

    # Flush this ticker's rows to CSV immediately
    if ticker_rows:
        chunk_df = pd.DataFrame(ticker_rows, columns=CSV_COLUMNS)
        chunk_df.to_csv(RAW_PATH, mode='a', header=(not _wrote_header),
                        index=False)
        _wrote_header = True
        total_rows_written += len(ticker_rows)
        del chunk_df
    del ticker_rows

    tickers_processed += 1

elapsed = time.time() - t0
print(f"\nStep 2 done: {total_rows_written:,} qualified bars from "
      f"{tickers_processed} tickers ({elapsed:.0f}s)")
print(f"API calls: {api_ok} ok, {api_fail} fail")
print(f"💾 Raw data saved incrementally: {RAW_PATH}")

if total_rows_written == 0:
    print("❌ No data collected. Exiting.")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# STEP 3 — READ BACK RAW DATA FOR ANALYSIS (chunked)
# ═══════════════════════════════════════════════════════════════

print("\n⏳ Reading raw CSV back for analysis...")
df = pd.read_csv(RAW_PATH)
print(f"   Loaded {len(df):,} rows")

# ═══════════════════════════════════════════════════════════════
# STEP 4 — SUMMARY TABLE BY BUCKET + CONTEXT
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("STEP 4: Building summary tables")
print("=" * 72)

# Set categorical ordering for buckets
df['bucket'] = pd.Categorical(df['bucket'], categories=BUCKET_LABELS, ordered=True)

summary_rows = []

for ctx in ['LONG', 'SHORT']:
    ctx_df = df[df['context'] == ctx]
    for bkt in BUCKET_LABELS:
        bkt_df = ctx_df[ctx_df['bucket'] == bkt]
        n = len(bkt_df)
        if n == 0:
            continue

        row = {
            'context': ctx,
            'bucket': bkt,
            'n': n,
        }

        for fwd_n in FORWARD_BARS:
            col_pb   = f'pb_any_{fwd_n}'
            col_dep  = f'pb_depth_{fwd_n}'
            col_cont = f'continuation_{fwd_n}'

            valid = bkt_df[col_pb].dropna()
            row[f'pullback_pct_{fwd_n}bar']     = round(valid.mean() * 100, 1) if len(valid) else np.nan
            dep = bkt_df[col_dep].dropna()
            row[f'med_depth_{fwd_n}bar']         = round(dep.median(), 2) if len(dep) else np.nan
            row[f'p90_depth_{fwd_n}bar']         = round(dep.quantile(0.90), 2) if len(dep) else np.nan
            cont = bkt_df[col_cont].dropna()
            row[f'continuation_rate_{fwd_n}bar'] = round(cont.mean() * 100, 1) if len(cont) else np.nan

        rec = bkt_df['recover_within_6'].dropna()
        row['recover_6bar_pct'] = round(rec.mean() * 100, 1) if len(rec) else np.nan

        summary_rows.append(row)

summary = pd.DataFrame(summary_rows)

summary_path = os.path.join(OUTPUT_DIR, 'summary_by_bucket_context.csv')
summary.to_csv(summary_path, index=False)
print(f"💾 Summary saved: {summary_path}")

# ── Also make a combined (context-agnostic) summary ──────────
combo_rows = []
for bkt in BUCKET_LABELS:
    bkt_df = df[df['bucket'] == bkt]
    n = len(bkt_df)
    if n == 0:
        continue
    row = {'bucket': bkt, 'n': n}
    for fwd_n in FORWARD_BARS:
        valid = bkt_df[f'pb_any_{fwd_n}'].dropna()
        row[f'pullback_pct_{fwd_n}bar']     = round(valid.mean() * 100, 1) if len(valid) else np.nan
        dep = bkt_df[f'pb_depth_{fwd_n}'].dropna()
        row[f'med_depth_{fwd_n}bar']         = round(dep.median(), 2) if len(dep) else np.nan
        row[f'p90_depth_{fwd_n}bar']         = round(dep.quantile(0.90), 2) if len(dep) else np.nan
        cont = bkt_df[f'continuation_{fwd_n}'].dropna()
        row[f'continuation_rate_{fwd_n}bar'] = round(cont.mean() * 100, 1) if len(cont) else np.nan
    rec = bkt_df['recover_within_6'].dropna()
    row['recover_6bar_pct'] = round(rec.mean() * 100, 1) if len(rec) else np.nan
    combo_rows.append(row)

combo = pd.DataFrame(combo_rows)
combo_path = os.path.join(OUTPUT_DIR, 'summary_combined.csv')
combo.to_csv(combo_path, index=False)
print(f"💾 Combined summary saved: {combo_path}")

# ═══════════════════════════════════════════════════════════════
# STEP 5 — HTML BAR CHART (pullback frequency by bucket)
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("STEP 5: Building HTML chart")
print("=" * 72)

import plotly.graph_objects as go

fig = go.Figure()

# One grouped bar per forward window
colors = {'1': '#ef5350', '3': '#ffa726', '6': '#66bb6a'}

for fwd_n in FORWARD_BARS:
    vals = []
    for bkt in BUCKET_LABELS:
        match = combo[combo['bucket'] == bkt]
        if len(match):
            vals.append(match.iloc[0][f'pullback_pct_{fwd_n}bar'])
        else:
            vals.append(0)
    fig.add_trace(go.Bar(
        name=f'Next {fwd_n} bar(s)',
        x=BUCKET_LABELS,
        y=vals,
        marker_color=colors[str(fwd_n)],
        text=[f'{v:.1f}%' if pd.notna(v) else '' for v in vals],
        textposition='outside',
    ))

fig.update_layout(
    template='plotly_dark',
    title='Single-Bar ATR Exhaustion — Pullback Frequency by Bucket',
    barmode='group',
    xaxis_title='ATR Consumption Bucket',
    yaxis_title='% of Bars Followed by Pullback',
    height=550,
    margin=dict(l=60, r=30, t=60, b=40),
)

chart_path = os.path.join(OUTPUT_DIR, 'pullback_frequency_by_bucket.html')
fig.write_html(chart_path)
print(f"📊 Chart saved: {chart_path}")

# ── Second chart: median pullback depth by bucket ────────────
fig2 = go.Figure()

for fwd_n in FORWARD_BARS:
    vals = []
    for bkt in BUCKET_LABELS:
        match = combo[combo['bucket'] == bkt]
        if len(match):
            vals.append(match.iloc[0][f'med_depth_{fwd_n}bar'])
        else:
            vals.append(0)
    fig2.add_trace(go.Bar(
        name=f'Next {fwd_n} bar(s)',
        x=BUCKET_LABELS,
        y=vals,
        marker_color=colors[str(fwd_n)],
        text=[f'{v:.2f}%' if pd.notna(v) else '' for v in vals],
        textposition='outside',
    ))

fig2.update_layout(
    template='plotly_dark',
    title='Single-Bar ATR Exhaustion — Median Pullback Depth by Bucket',
    barmode='group',
    xaxis_title='ATR Consumption Bucket',
    yaxis_title='Median Pullback Depth (% of ATR)',
    height=550,
    margin=dict(l=60, r=30, t=60, b=40),
)

depth_chart_path = os.path.join(OUTPUT_DIR, 'pullback_depth_by_bucket.html')
fig2.write_html(depth_chart_path)
print(f"📊 Depth chart saved: {depth_chart_path}")

# ── Third chart: continuation vs reversal by context ─────────
fig3 = go.Figure()

for ctx in ['LONG', 'SHORT']:
    ctx_summary = summary[summary['context'] == ctx]
    vals = []
    for bkt in BUCKET_LABELS:
        match = ctx_summary[ctx_summary['bucket'] == bkt]
        if len(match):
            vals.append(match.iloc[0]['continuation_rate_3bar'])
        else:
            vals.append(0)
    fig3.add_trace(go.Bar(
        name=f'{ctx} context',
        x=BUCKET_LABELS,
        y=vals,
        text=[f'{v:.1f}%' if pd.notna(v) else '' for v in vals],
        textposition='outside',
    ))

fig3.update_layout(
    template='plotly_dark',
    title='3-Bar Continuation Rate by Bucket & Context',
    barmode='group',
    xaxis_title='ATR Consumption Bucket',
    yaxis_title='Continuation Rate (%)',
    height=550,
    margin=dict(l=60, r=30, t=60, b=40),
)

context_chart_path = os.path.join(OUTPUT_DIR, 'continuation_by_context.html')
fig3.write_html(context_chart_path)
print(f"📊 Context chart saved: {context_chart_path}")

# ═══════════════════════════════════════════════════════════════
# STEP 6 — PRINT FULL SUMMARY
# ═══════════════════════════════════════════════════════════════

total_elapsed = time.time() - t0

print("\n" + "=" * 72)
print("COMBINED SUMMARY (all contexts)")
print("=" * 72)
print(combo.to_string(index=False))

print("\n" + "=" * 72)
print("BY CONTEXT — LONG (bar closed above day open)")
print("=" * 72)
long_summary = summary[summary['context'] == 'LONG']
if not long_summary.empty:
    print(long_summary.to_string(index=False))

print("\n" + "=" * 72)
print("BY CONTEXT — SHORT (bar closed below day open)")
print("=" * 72)
short_summary = summary[summary['context'] == 'SHORT']
if not short_summary.empty:
    print(short_summary.to_string(index=False))

print("\n" + "=" * 72)
print("KEY FINDINGS")
print("=" * 72)

# Highlight the threshold where pullback rate jumps
if not combo.empty:
    for _, r in combo.iterrows():
        bkt = r['bucket']
        n   = int(r['n'])
        pb1 = r.get('pullback_pct_1bar', 0)
        pb3 = r.get('pullback_pct_3bar', 0)
        d3  = r.get('med_depth_3bar', 0)
        c3  = r.get('continuation_rate_3bar', 0)
        rec = r.get('recover_6bar_pct', 0)
        print(f"  {bkt:12s}  n={n:>8,}  | 1-bar PB {pb1:5.1f}%  "
              f"3-bar PB {pb3:5.1f}%  depth {d3:5.2f}%  "
              f"cont {c3:5.1f}%  rec6 {rec:5.1f}%")

    # Find the real threshold
    non_normal = combo[combo['bucket'] != 'NORMAL']
    if not non_normal.empty:
        best_idx = non_normal['pullback_pct_3bar'].idxmax()
        best = non_normal.loc[best_idx]
        norml = combo[combo['bucket'] == 'NORMAL']
        if not norml.empty:
            n_pb = norml.iloc[0]['pullback_pct_3bar']
            diff = best['pullback_pct_3bar'] - n_pb
            print(f"\n🎯 Biggest pullback rate jump vs NORMAL at "
                  f"{best['bucket']}: +{diff:.1f}pp "
                  f"({n_pb:.1f}% → {best['pullback_pct_3bar']:.1f}%)")

print(f"\n⏱  Total runtime: {total_elapsed:.0f}s")
print(f"💾 All outputs in: {OUTPUT_DIR}")
print("=" * 72)

"""
Gap-Up 3%+ EARNINGS ONLY — TrendStrength Candle Forward Returns (1-20 Days)
============================================================================
Tests whether TrendStrength candle colour on 3%+ EARNINGS gap-up days
predicts forward returns over 1-20 trading days.

EARNINGS DATES: yfinance (primary) → FMP (fallback)
Population     : Full watchlist (~237 tickers), 2020-01-01 to present
Gap filter     : (Open[t] - Close[t-1]) / Close[t-1] >= 3%, ON earnings day
Entry          : Gap-day close (hold from close)
Tiers          : 7-tier TrendStrength cs breakdown + binary rollup

Outputs ->  studies/gapup_earnings_trendstrength_daily/outputs/
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import warnings
warnings.filterwarnings("ignore")

import time
from datetime import datetime, time as dtime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import yaml
import yfinance as yf

from shared.data_router import DataRouter
from shared.watchlist import get_watchlist
from shared.indicators.trend_strength_candles import TrendStrengthCandles
from shared.chart_builder import ChartBuilder

# -- Paths ----------------------------------------------------------------
STUDY_DIR = Path(r'C:\QuantLab\Data_Lab\studies\gapup_earnings_trendstrength_daily')
OUTPUT_DIR = STUDY_DIR / 'outputs'
CHART_DIR = OUTPUT_DIR / 'charts'
CHART_DIR.mkdir(parents=True, exist_ok=True)

# -- Config ---------------------------------------------------------------
with open(STUDY_DIR / 'config.yaml', 'r') as f:
    cfg = yaml.safe_load(f)

START_DATE      = cfg['start_date']
GAP_THRESHOLD   = cfg['gap_threshold']
WARMUP_BARS     = cfg['warmup_bars']
HOLDING_PERIODS = cfg['holding_periods']
TOLERANCE_DAYS  = cfg['earnings_match_tolerance_days']

# -- TrendStrength tier classification ------------------------------------
TIER_ORDER = [
    'STRONG_BULL', 'BULL', 'WEAK_BULL', 'NEUTRAL',
    'WEAK_BEAR', 'BEAR', 'STRONG_BEAR',
]

TIER_COLORS = {
    'STRONG_BULL': '#00e5ff',
    'BULL':        '#26a69a',
    'WEAK_BULL':   '#81c784',
    'NEUTRAL':     '#fdd835',
    'WEAK_BEAR':   '#ff8a65',
    'BEAR':        '#ef5350',
    'STRONG_BEAR': '#e040fb',
}

BINARY_MAP = {
    'STRONG_BULL': 'BULLISH',
    'BULL':        'BULLISH',
    'WEAK_BULL':   'BULLISH',
    'NEUTRAL':     'NEUTRAL',
    'WEAK_BEAR':   'BEARISH',
    'BEAR':        'BEARISH',
    'STRONG_BEAR': 'BEARISH',
}


def classify_tier(cs_val: float) -> str:
    if cs_val >= 70:   return 'STRONG_BULL'
    if cs_val >= 40:   return 'BULL'
    if cs_val >= 15:   return 'WEAK_BULL'
    if cs_val <= -70:  return 'STRONG_BEAR'
    if cs_val <= -40:  return 'BEAR'
    if cs_val <= -15:  return 'WEAK_BEAR'
    return 'NEUTRAL'


# =========================================================================
# EARNINGS DATE FETCHING
# =========================================================================
def fetch_earnings_dates_yf(ticker: str) -> set:
    """Fetch earnings reaction dates from yfinance.
    Returns set of date strings (YYYY-MM-DD) representing the SESSION
    where the earnings gap would appear (handles BMO/AMC mapping).
    """
    try:
        tkr = yf.Ticker(ticker)
        ed = tkr.earnings_dates
        if ed is None or ed.empty:
            return set()

        dates = set()
        for ts in ed.index:
            try:
                if hasattr(ts, "tz_convert"):
                    et_ts = ts.tz_convert("America/New_York")
                else:
                    et_ts = ts
                t = et_ts.time()
                # After close (>= 16:00) -> gap appears NEXT session
                if t >= dtime(16, 0):
                    next_date = (et_ts + pd.Timedelta(days=1)).date()
                    dates.add(next_date.strftime("%Y-%m-%d"))
                # Pre-market (< 9:30) -> gap appears THIS session
                elif t < dtime(9, 30):
                    dates.add(et_ts.date().strftime("%Y-%m-%d"))
                else:
                    dates.add(et_ts.date().strftime("%Y-%m-%d"))
            except Exception:
                pass
        return dates
    except Exception:
        return set()


def fetch_earnings_dates_fmp(ticker: str) -> set:
    """Fallback: fetch earnings dates from FMP historical earnings calendar."""
    try:
        from shared.config.api_clients import FMPClient
        fmp = FMPClient()
        url = f"{fmp.base_url}/historical/earning_calendar/{ticker}"
        resp = requests.get(url, params={'apikey': fmp.api_key, 'limit': 200}, timeout=10)
        if resp.status_code != 200:
            return set()
        data = resp.json()
        if not isinstance(data, list):
            return set()

        dates = set()
        for rec in data:
            ann_date = rec.get('date', '')
            time_label = str(rec.get('time', '')).lower()
            if not ann_date:
                continue
            try:
                dt = pd.Timestamp(ann_date)
                if time_label in ('amc', 'after market close') or '16:' in time_label:
                    next_date = (dt + pd.Timedelta(days=1)).date()
                    dates.add(next_date.strftime("%Y-%m-%d"))
                else:
                    dates.add(dt.date().strftime("%Y-%m-%d"))
            except Exception:
                pass
        return dates
    except Exception:
        return set()


def is_near_earnings(gap_date_str: str, earnings_dates: set, tolerance: int = 1) -> bool:
    """Check if a gap date is within +/- tolerance calendar days of an earnings date."""
    try:
        gap_dt = pd.Timestamp(gap_date_str).normalize()
        for ed_str in earnings_dates:
            ed_dt = pd.Timestamp(ed_str).normalize()
            if abs((gap_dt - ed_dt).days) <= tolerance:
                return True
        return False
    except Exception:
        return False


# =========================================================================
# PHASE 1: DATA COLLECTION & GAP DETECTION (EARNINGS ONLY)
# =========================================================================
def collect_events() -> pd.DataFrame:
    tickers = get_watchlist()
    ts_indicator = TrendStrengthCandles()
    all_events = []
    failed = []
    earnings_stats = {'yf': 0, 'fmp': 0, 'none': 0, 'total_dates': 0}

    etf_skip = {
        'SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLE', 'XLK', 'XLV', 'XLI',
        'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC', 'XBI', 'XHB', 'XME',
        'ARKK', 'ARKG', 'ARKF', 'ARKW', 'TLT', 'HYG', 'GLD', 'SLV',
        'USO', 'VXX', 'UVXY', 'SQQQ', 'TQQQ', 'SPXU', 'SOXL', 'SOXS',
        'LABU', 'LABD', 'KWEB', 'EEM', 'FXI', 'GDX', 'GDXJ', 'SMH',
        'VNQ', 'TNA', 'TZA', 'JETS', 'MSOS', 'BITX', 'IBIT', 'BITO',
    }

    tickers_to_scan = [t for t in tickers if t not in etf_skip]

    print(f"Scanning {len(tickers_to_scan)} tickers (skipping {len(tickers) - len(tickers_to_scan)} ETFs)")
    print(f"Filter: >={GAP_THRESHOLD*100:.0f}% gap-up on EARNINGS days since {START_DATE}")
    print(f"Fetching earnings dates (yfinance primary, FMP fallback)...\n")

    for i, ticker in enumerate(tickers_to_scan, 1):
        if i % 25 == 0 or i == len(tickers_to_scan):
            print(f"  [{i}/{len(tickers_to_scan)}] {ticker}... "
                  f"(events so far: {len(all_events)})")

        # -- Step 1: Get earnings dates -----------------------------------
        earnings_dates = fetch_earnings_dates_yf(ticker)
        source = 'yf'
        if not earnings_dates:
            earnings_dates = fetch_earnings_dates_fmp(ticker)
            source = 'fmp'
            if earnings_dates:
                time.sleep(0.5)

        if not earnings_dates:
            earnings_stats['none'] += 1
            continue
        else:
            earnings_stats[source] = earnings_stats.get(source, 0) + 1
            earnings_stats['total_dates'] += len(earnings_dates)

        # -- Step 2: Get price data ---------------------------------------
        try:
            df = DataRouter.get_price_data(
                ticker, START_DATE, timeframe='daily',
                study_type='returns', fallback=True,
            )
            if df is None or len(df) < WARMUP_BARS + 50:
                failed.append((ticker, 'insufficient data'))
                continue

            df = ts_indicator.compute(df)
            df = df.iloc[WARMUP_BARS:].copy()
            if len(df) < 30:
                failed.append((ticker, 'too short after warmup'))
                continue

            # -- Step 3: Detect gap-ups -----------------------------------
            prev_close = df['Close'].shift(1)
            gap_pct = (df['Open'] - prev_close) / prev_close
            gap_mask = gap_pct >= GAP_THRESHOLD
            gap_indices = df.index[gap_mask]

            if len(gap_indices) == 0:
                continue

            dates_sorted = sorted(df.index.tolist())
            close_map = df['Close'].to_dict()
            date_to_pos = {d: idx for idx, d in enumerate(dates_sorted)}

            for dt in gap_indices:
                gap_date_str = pd.Timestamp(dt).strftime("%Y-%m-%d")

                # -- Step 4: EARNINGS FILTER ------------------------------
                if not is_near_earnings(gap_date_str, earnings_dates, TOLERANCE_DAYS):
                    continue

                cs_val = df.loc[dt, 'cs']
                if pd.isna(cs_val):
                    continue

                entry_close = close_map[dt]
                if pd.isna(entry_close) or entry_close <= 0:
                    continue

                pos = date_to_pos[dt]
                tier = classify_tier(cs_val)

                event = {
                    'ticker': ticker,
                    'date': dt,
                    'open': df.loc[dt, 'Open'],
                    'close': entry_close,
                    'prev_close': prev_close.loc[dt],
                    'gap_pct': gap_pct.loc[dt] * 100,
                    'cs': round(cs_val, 2),
                    'tier': tier,
                    'binary': BINARY_MAP[tier],
                }

                for days in HOLDING_PERIODS:
                    fwd_pos = pos + days
                    if fwd_pos < len(dates_sorted):
                        fwd_close = close_map[dates_sorted[fwd_pos]]
                        event[f'T{days}_return'] = (fwd_close - entry_close) / entry_close * 100
                    else:
                        event[f'T{days}_return'] = np.nan

                all_events.append(event)

        except Exception as e:
            failed.append((ticker, str(e)[:80]))
            continue

    df_events = pd.DataFrame(all_events)
    print(f"\n{'='*60}")
    print(f"  Collection complete: {len(df_events)} EARNINGS gap events "
          f"from {df_events['ticker'].nunique() if len(df_events) else 0} tickers")
    print(f"  Earnings sources: yfinance={earnings_stats['yf']}, "
          f"FMP={earnings_stats['fmp']}, none={earnings_stats['none']}")
    print(f"  Total earnings dates fetched: {earnings_stats['total_dates']}")
    if failed:
        print(f"  {len(failed)} tickers failed/skipped")
    print(f"{'='*60}")
    return df_events


# =========================================================================
# PHASE 2: AGGREGATION & METRICS
# =========================================================================
def compute_stats(df_events: pd.DataFrame) -> dict:
    return_cols = [f'T{d}_return' for d in HOLDING_PERIODS]
    results = {}

    for group_col, group_order in [('tier', TIER_ORDER), ('binary', ['BULLISH', 'NEUTRAL', 'BEARISH'])]:
        group_stats = {}
        for grp in group_order:
            subset = df_events[df_events[group_col] == grp]
            n = len(subset)
            if n == 0:
                continue

            stats_row = {'n': n}
            if n < 10:
                stats_row['confidence'] = '❌ INSUFFICIENT'
            elif n < 20:
                stats_row['confidence'] = '⚠️ LOW'
            else:
                stats_row['confidence'] = '✅ RELIABLE'

            for col in return_cols:
                vals = subset[col].dropna()
                nn = len(vals)
                if nn == 0:
                    for sfx in ['_winrate', '_mean', '_median', '_std',
                                '_avg_winner', '_avg_loser', '_profit_factor']:
                        stats_row[f'{col}{sfx}'] = np.nan
                    continue

                wins = vals[vals > 0]
                losses = vals[vals <= 0]
                stats_row[f'{col}_winrate'] = len(wins) / nn
                stats_row[f'{col}_mean'] = vals.mean()
                stats_row[f'{col}_median'] = vals.median()
                stats_row[f'{col}_std'] = vals.std()
                stats_row[f'{col}_avg_winner'] = wins.mean() if len(wins) > 0 else 0
                stats_row[f'{col}_avg_loser'] = losses.mean() if len(losses) > 0 else 0
                gp = wins.sum() if len(wins) > 0 else 0
                gl = abs(losses.sum()) if len(losses) > 0 else 0
                stats_row[f'{col}_profit_factor'] = gp / gl if gl > 0 else np.inf

            group_stats[grp] = stats_row
        results[group_col] = group_stats

    return results


# =========================================================================
# PHASE 3: VISUALIZATION
# =========================================================================
def build_charts(df_events: pd.DataFrame, stats: dict):
    tier_stats = stats['tier']
    key_horizons = [1, 3, 5, 10, 15, 20]

    # -- 1. Win Rate Heatmap (7-tier) ------------------------------------
    wr_data = {}
    for tier in TIER_ORDER:
        if tier not in tier_stats:
            continue
        s = tier_stats[tier]
        row = {}
        for d in HOLDING_PERIODS:
            row[f'T+{d}'] = s.get(f'T{d}_return_winrate', np.nan)
        wr_data[f"{tier} (n={s['n']})"] = row

    if wr_data:
        df_wr = pd.DataFrame(wr_data).T
        ChartBuilder.winrate_heatmap(
            df_wr,
            'EARNINGS Gap-Up >=3% - Win Rate by TrendStrength Tier (1-20 Days)',
            save_path=CHART_DIR / 'winrate_heatmap.html',
        )
        print("  saved winrate_heatmap.html")

    # -- 2. Forward Returns Grouped Bar (binary rollup) ------------------
    binary_stats = stats['binary']
    fr_data = {}
    for grp in ['BULLISH', 'NEUTRAL', 'BEARISH']:
        if grp not in binary_stats:
            continue
        s = binary_stats[grp]
        row = {}
        for d in key_horizons:
            row[f'+{d}d'] = round(s.get(f'T{d}_return_mean', 0), 3)
        fr_data[f"{grp} (n={s['n']})"] = row

    if fr_data:
        ChartBuilder.forward_returns(
            fr_data,
            'EARNINGS Gap-Up >=3% - Avg Forward Return: Bullish vs Bearish Candle',
            save_path=CHART_DIR / 'forward_returns_binary.html',
        )
        print("  saved forward_returns_binary.html")

    # -- 3. Multi-Line Win Rate Curve (7-tier) ---------------------------
    fig = go.Figure()
    for tier in TIER_ORDER:
        if tier not in tier_stats:
            continue
        s = tier_stats[tier]
        y_vals = [s.get(f'T{d}_return_winrate', np.nan) for d in HOLDING_PERIODS]
        fig.add_trace(go.Scatter(
            x=[f'T+{d}' for d in HOLDING_PERIODS],
            y=y_vals,
            mode='lines+markers',
            name=f"{tier} (n={s['n']})",
            line=dict(color=TIER_COLORS[tier], width=2.5),
            marker=dict(size=5),
        ))
    fig.add_hline(y=0.5, line_dash='dot', line_color='white', line_width=0.8,
                  annotation_text='50%')
    fig.update_layout(
        template='plotly_dark',
        title='EARNINGS Gap-Up >=3% - Win Rate Curve by TrendStrength Tier (1-20 Days)',
        xaxis_title='Holding Period',
        yaxis_title='Win Rate',
        yaxis_tickformat='.0%',
        height=550,
        margin=dict(l=60, r=30, t=50, b=30),
        legend=dict(font=dict(size=11)),
    )
    fig.write_html(str(CHART_DIR / 'winrate_curve.html'))
    print("  saved winrate_curve.html")

    # -- 4. Multi-Line Avg Return Curve (7-tier) -------------------------
    fig2 = go.Figure()
    for tier in TIER_ORDER:
        if tier not in tier_stats:
            continue
        s = tier_stats[tier]
        y_vals = [s.get(f'T{d}_return_mean', np.nan) for d in HOLDING_PERIODS]
        fig2.add_trace(go.Scatter(
            x=[f'T+{d}' for d in HOLDING_PERIODS],
            y=y_vals,
            mode='lines+markers',
            name=f"{tier} (n={s['n']})",
            line=dict(color=TIER_COLORS[tier], width=2.5),
            marker=dict(size=5),
        ))
    fig2.add_hline(y=0, line_dash='dot', line_color='white', line_width=0.8)
    fig2.update_layout(
        template='plotly_dark',
        title='EARNINGS Gap-Up >=3% - Avg Return Curve by TrendStrength Tier (1-20 Days)',
        xaxis_title='Holding Period',
        yaxis_title='Mean Return (%)',
        height=550,
        margin=dict(l=60, r=30, t=50, b=30),
        legend=dict(font=dict(size=11)),
    )
    fig2.write_html(str(CHART_DIR / 'avg_return_curve.html'))
    print("  saved avg_return_curve.html")

    # -- 5. Gap Size Distribution ----------------------------------------
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(
        x=df_events['gap_pct'], nbinsx=40,
        marker_color='#42a5f5', opacity=0.85,
    ))
    fig3.update_layout(
        template='plotly_dark',
        title='EARNINGS Gap-Up >=3% - Gap Size Distribution',
        xaxis_title='Gap Size (%)', yaxis_title='Count',
        height=400, margin=dict(l=60, r=30, t=50, b=30),
    )
    fig3.write_html(str(CHART_DIR / 'gap_distribution.html'))
    print("  saved gap_distribution.html")

    # -- 6. Forward Returns by Tier (all 7 at key horizons) --------------
    tier_fr = {}
    for tier in TIER_ORDER:
        if tier not in tier_stats:
            continue
        s = tier_stats[tier]
        row = {}
        for d in key_horizons:
            row[f'+{d}d'] = round(s.get(f'T{d}_return_mean', 0), 3)
        tier_fr[f"{tier} (n={s['n']})"] = row

    if tier_fr:
        ChartBuilder.forward_returns(
            tier_fr,
            'EARNINGS Gap-Up >=3% - Avg Forward Return by TrendStrength Tier',
            save_path=CHART_DIR / 'forward_returns_7tier.html',
        )
        print("  saved forward_returns_7tier.html")


# =========================================================================
# PHASE 4: SUMMARY TABLE & TEXT OUTPUT
# =========================================================================
def print_summary(df_events: pd.DataFrame, stats: dict):
    print("\n" + "=" * 80)
    print("  EARNINGS GAP-UP >=3% - TRENDSTRENGTH CANDLE FORWARD RETURNS (1-20 DAYS)")
    print("=" * 80)
    print(f"  Total events: {len(df_events)} | Unique tickers: {df_events['ticker'].nunique()}")
    print(f"  Date range: {df_events['date'].min()} to {df_events['date'].max()}")
    print(f"  Avg gap size: {df_events['gap_pct'].mean():.1f}% | Median: {df_events['gap_pct'].median():.1f}%")

    # Tier distribution
    print(f"\n-- TIER DISTRIBUTION -----------------------------------------")
    for tier in TIER_ORDER:
        n = len(df_events[df_events['tier'] == tier])
        pct = n / len(df_events) * 100 if len(df_events) > 0 else 0
        print(f"  {tier:<15} {n:>5} ({pct:>5.1f}%)")

    # 7-Tier Summary
    print(f"\n-- 7-TIER BREAKDOWN ------------------------------------------")
    header = f"{'Tier':<15} {'n':>5}  {'Conf':<14} {'T+1 WR':>7} {'T+5 WR':>7} {'T+10 WR':>7} {'T+20 WR':>7}  {'T+5 Avg':>7} {'T+20 Avg':>8}"
    print(header)
    print("-" * len(header))

    tier_stats = stats['tier']
    for tier in TIER_ORDER:
        if tier not in tier_stats:
            print(f"  {tier:<15}   0   (no events)")
            continue
        s = tier_stats[tier]
        n = s['n']
        conf = s['confidence']

        def fmt_wr(v):
            return f"{v:.1%}" if not np.isnan(v) else "  N/A"
        def fmt_ret(v):
            return f"{v:+.2f}%" if not np.isnan(v) else "  N/A"

        t1wr  = s.get('T1_return_winrate', np.nan)
        t5wr  = s.get('T5_return_winrate', np.nan)
        t10wr = s.get('T10_return_winrate', np.nan)
        t20wr = s.get('T20_return_winrate', np.nan)
        t5avg = s.get('T5_return_mean', np.nan)
        t20avg = s.get('T20_return_mean', np.nan)

        print(f"  {tier:<15} {n:>4}  {conf:<14} {fmt_wr(t1wr):>7} {fmt_wr(t5wr):>7} {fmt_wr(t10wr):>7} {fmt_wr(t20wr):>7}  {fmt_ret(t5avg):>7} {fmt_ret(t20avg):>8}")

    # Binary rollup
    print("\n-- BINARY ROLLUP (BULLISH vs BEARISH vs NEUTRAL) -------------")
    binary_stats = stats['binary']
    for grp in ['BULLISH', 'NEUTRAL', 'BEARISH']:
        if grp not in binary_stats:
            continue
        s = binary_stats[grp]
        n = s['n']
        print(f"\n  {grp} (n={n}) {s['confidence']}")
        for d in [1, 3, 5, 10, 15, 20]:
            wr = s.get(f'T{d}_return_winrate', np.nan)
            avg = s.get(f'T{d}_return_mean', np.nan)
            med = s.get(f'T{d}_return_median', np.nan)
            pf = s.get(f'T{d}_return_profit_factor', np.nan)
            wr_s = f"{wr:.1%}" if not np.isnan(wr) else "N/A"
            avg_s = f"{avg:+.2f}%" if not np.isnan(avg) else "N/A"
            med_s = f"{med:+.2f}%" if not np.isnan(med) else "N/A"
            pf_s = f"{pf:.2f}" if not np.isnan(pf) and pf != np.inf else ("inf" if pf == np.inf else "N/A")
            print(f"    T+{d:>2}: WR={wr_s:>6}  Avg={avg_s:>8}  Med={med_s:>8}  PF={pf_s:>5}")

    # Save summary CSV
    rows = []
    for tier in TIER_ORDER:
        if tier not in tier_stats:
            continue
        s = tier_stats[tier]
        for d in HOLDING_PERIODS:
            rows.append({
                'tier': tier,
                'binary': BINARY_MAP.get(tier, ''),
                'n': s['n'],
                'confidence': s['confidence'],
                'holding_days': d,
                'win_rate': s.get(f'T{d}_return_winrate', np.nan),
                'mean_return': s.get(f'T{d}_return_mean', np.nan),
                'median_return': s.get(f'T{d}_return_median', np.nan),
                'std': s.get(f'T{d}_return_std', np.nan),
                'avg_winner': s.get(f'T{d}_return_avg_winner', np.nan),
                'avg_loser': s.get(f'T{d}_return_avg_loser', np.nan),
                'profit_factor': s.get(f'T{d}_return_profit_factor', np.nan),
            })
    df_summary = pd.DataFrame(rows)
    df_summary.to_csv(OUTPUT_DIR / 'summary_stats.csv', index=False)
    print(f"\nSaved summary_stats.csv ({len(df_summary)} rows)")


# =========================================================================
# MAIN
# =========================================================================
if __name__ == '__main__':
    start = datetime.now()

    # Phase 1: Collect
    df_events = collect_events()
    if df_events.empty:
        print("No earnings gap events found. Check data and thresholds.")
        sys.exit(1)

    # Save events
    df_events.to_csv(OUTPUT_DIR / 'events.csv', index=False)
    print(f"Saved events.csv ({len(df_events)} events)")

    # Phase 2: Aggregate
    stats = compute_stats(df_events)

    # Phase 3: Charts
    print("\nGenerating charts...")
    build_charts(df_events, stats)

    # Phase 4: Summary
    print_summary(df_events, stats)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nTotal runtime: {elapsed:.0f}s")
    print("Study complete.")

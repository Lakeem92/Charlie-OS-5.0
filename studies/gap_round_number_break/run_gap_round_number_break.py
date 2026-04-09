#!/usr/bin/env python3
"""
STUDY: Earnings Gap + Round Number Break + Candle Color Analysis
================================================================
"Does momentum confirmation matter when a structural level breaks
on a catalyst gap day?"

RESEARCH QUESTION
-----------------
Lakeem's identified bottleneck: hesitating on structural level breaks
when TrendStrength candles show neutral/gray color, even when the
catalyst and options structure both support the trade. This study
measures whether candle color at the moment of a round-number break
(call wall proxy) actually predicts forward returns on catalyst gap days,
or whether the structural break itself IS the signal.

Run from repo root:
    cd C:\\QuantLab\\Data_Lab
    python studies/gap_round_number_break/run_gap_round_number_break.py
"""

from __future__ import annotations

import os
import sys
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

# ── Path Setup ───────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
for _p in [ROOT, os.path.join(ROOT, 'shared'), os.path.join(ROOT, 'shared', 'indicators'),
           os.path.join(ROOT, 'shared', 'config')]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shared.data_router import DataRouter
from shared.watchlist import get_watchlist
from shared.indicators.trend_strength_nr7 import compute_trend_strength_nr7, TrendStrengthParams

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

UNIVERSE               = get_watchlist()   # Full ~240 name watchlist
START_DATE             = '2024-01-01'
END_DATE               = '2026-03-06'
TIMEFRAME              = '5min'            # 5-minute bars for intraday analysis
GAP_THRESHOLD          = 0.05             # 5% minimum gap (catalyst proxy)
ROUND_NUMBER_INCREMENT = 5                # $5 round numbers as call wall proxy
SESSION_START_MINUTES  = 5               # First bar = opening range
MAX_BREAK_WINDOW_BARS  = 78              # Full session bar count (6.5 hours)

# TrendStrength consensus score thresholds (match TOS indicator)
CYAN_THRESHOLD  =  70    # cs >= 70   → MAX BULL (cyan)
GREEN_THRESHOLD =  30    # cs 30–70   → moderate bull (green)
GRAY_THRESHOLD  = -30    # cs -30–30  → neutral (gray)
                         # cs < -30   → bearish (red)

# Forward return measurement windows (in 5-min bars)
FORWARD_WINDOWS = {
    '15min': 3,
    '30min': 6,
    '1hr':   12,
    '2hr':   24,
    'EOD':   None,       # Special case: measure to session close
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def cs_to_color(cs: float) -> str:
    """Map consensus score to candle color label."""
    if cs >= CYAN_THRESHOLD:
        return 'CYAN'
    elif cs >= GREEN_THRESHOLD:
        return 'GREEN'
    elif cs >= GRAY_THRESHOLD:
        return 'GRAY'
    else:
        return 'RED'


def classify_timing(bar_idx: int) -> str:
    if bar_idx <= 5:
        return 'FIRST_30MIN'
    elif bar_idx <= 11:
        return '30_TO_60MIN'
    elif bar_idx <= 23:
        return '1HR_TO_2HR'
    else:
        return 'AFTER_2HR'


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — IDENTIFY GAP DAYS
# ─────────────────────────────────────────────────────────────────────────────

def collect_gap_events(universe: list[str]) -> pd.DataFrame:
    """Pull daily data for each ticker; return all 5%+ gap-up days."""
    all_gap_events: list[dict] = []

    for ticker in universe:
        try:
            daily = DataRouter.get_price_data(
                ticker, START_DATE, end_date=END_DATE, timeframe='daily'
            )
            if daily is None or len(daily) < 10:
                continue

            daily = daily.sort_index()
            daily['prior_close'] = daily['Close'].shift(1)
            daily['gap_pct']     = (daily['Open'] - daily['prior_close']) / daily['prior_close']

            for date, row in daily[daily['gap_pct'] >= GAP_THRESHOLD].iterrows():
                all_gap_events.append({
                    'ticker':      ticker,
                    'date':        date,
                    'prior_close': row['prior_close'],
                    'open_price':  row['Open'],
                    'gap_pct':     row['gap_pct'],
                    'day_close':   row['Close'],
                    'day_high':    row['High'],
                    'day_low':     row['Low'],
                })
        except Exception:
            continue

    df = pd.DataFrame(all_gap_events)
    print(f"Found {len(df)} gap-up events >= {GAP_THRESHOLD*100:.0f}% "
          f"across {df['ticker'].nunique() if len(df) else 0} tickers")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — INTRADAY ANALYSIS: TRENDSTRENGTH + ROUND NUMBER BREAK + ORB
# ─────────────────────────────────────────────────────────────────────────────

def analyze_gap_events(gap_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    For each gap event:
      • Pull 5-min intraday data (with 7-day warmup)
      • Compute TrendStrength consensus score
      • Identify nearest $5 round number above open; find first bar that closes above it
      • Record break candle color + forward returns
      • Record opening-range bar integrity (secondary ORB analysis)
    """
    break_events: list[dict] = []
    orb_events:   list[dict] = []

    for i, (_, event) in enumerate(gap_df.iterrows()):
        if i % 100 == 0:
            print(f"  [{i}/{len(gap_df)}] {event['ticker']} {str(event['date'])[:10]} ...")
        try:
            ticker     = event['ticker']
            event_date = pd.Timestamp(event['date'])

            warmup_start = (event_date - timedelta(days=7)).strftime('%Y-%m-%d')
            intra_end    = event_date.strftime('%Y-%m-%d')

            intraday = DataRouter.get_price_data(
                ticker, warmup_start, end_date=intra_end, timeframe=TIMEFRAME
            )
            if intraday is None or len(intraday) < 50:
                continue

            intraday = intraday.sort_index()

            # ── TrendStrength computation (needs warmup for z-scores) ──
            ts_result = compute_trend_strength_nr7(intraday, TrendStrengthParams())
            if ts_result is None or 'consensusScore' not in ts_result.columns:
                continue

            # Filter to event day only
            event_day = ts_result[ts_result.index.date == event_date.date()].copy()
            if len(event_day) < 10:
                continue

            # ── ORB (Secondary Analysis) ──────────────────────────────
            first_bar   = event_day.iloc[0]
            orb_high    = first_bar['High']
            orb_low     = first_bar['Low']
            orb_cs      = float(first_bar.get('consensusScore', 0))
            orb_color   = cs_to_color(orb_cs)
            rest        = event_day.iloc[1:]
            orb_broken  = bool((rest['Low'] < orb_low).any()) if len(rest) > 0 else False
            min_after   = rest['Low'].min() if len(rest) > 0 else orb_low

            orb_events.append({
                'ticker':                    ticker,
                'date':                      event_date,
                'gap_pct':                   event['gap_pct'],
                'open_price':                event['open_price'],
                'orb_high':                  orb_high,
                'orb_low':                   orb_low,
                'orb_candle_color':          orb_color,
                'orb_cs':                    orb_cs,
                'orb_low_broken':            orb_broken,
                'session_low':               event_day['Low'].min(),
                'max_drawdown_from_orb_low': (min_after - orb_low) / orb_low if orb_low > 0 else 0,
                'day_close':                 event['day_close'],
                'orb_break_return_eod':      (event['day_close'] - orb_high) / orb_high if orb_high > 0 else 0,
            })

            # ── Round Number Break (Primary Analysis) ─────────────────
            open_price  = float(event['open_price'])
            round_level = np.ceil(open_price / ROUND_NUMBER_INCREMENT) * ROUND_NUMBER_INCREMENT

            # If open is already sitting within 0.5% of the round number, use the next one
            if (round_level - open_price) / open_price < 0.005:
                round_level += ROUND_NUMBER_INCREMENT

            # Find first bar closing above round_level
            break_bar_idx: int | None = None
            for i in range(len(event_day)):
                if event_day.iloc[i]['Close'] > round_level:
                    break_bar_idx = i
                    break

            if break_bar_idx is None:
                break_events.append({
                    'ticker':                ticker,
                    'date':                  event_date,
                    'gap_pct':               event['gap_pct'],
                    'open_price':            open_price,
                    'round_level':           round_level,
                    'level_broken':          False,
                    'break_bar_idx':         None,
                    'break_bar_cs':          None,
                    'break_candle_color':    None,
                    'break_price':           None,
                    'break_time':            None,
                    'fwd_15m':               None,
                    'fwd_30m':               None,
                    'fwd_1hr':               None,
                    'fwd_2hr':               None,
                    'fwd_eod':               None,
                    'max_adverse_excursion': None,
                    'max_favorable_excursion': None,
                })
                continue

            break_bar  = event_day.iloc[break_bar_idx]
            break_price = float(break_bar['Close'])
            break_cs    = float(break_bar.get('consensusScore', 0))
            break_color = cs_to_color(break_cs)

            # Forward returns
            eod_price = float(event_day.iloc[-1]['Close'])
            fwd: dict[str, float | None] = {}
            for label, bars in FORWARD_WINDOWS.items():
                key = f'fwd_{label}'
                if bars is None:
                    fwd[key] = (eod_price - break_price) / break_price
                else:
                    target = break_bar_idx + bars
                    ref_price = (
                        float(event_day.iloc[target]['Close'])
                        if target < len(event_day)
                        else eod_price
                    )
                    fwd[key] = (ref_price - break_price) / break_price

            post_break = event_day.iloc[break_bar_idx:]
            mae = (post_break['Low'].min()  - break_price) / break_price
            mfe = (post_break['High'].max() - break_price) / break_price

            break_events.append({
                'ticker':                  ticker,
                'date':                    event_date,
                'gap_pct':                 event['gap_pct'],
                'open_price':              open_price,
                'round_level':             round_level,
                'level_broken':            True,
                'break_bar_idx':           break_bar_idx,
                'break_bar_cs':            break_cs,
                'break_candle_color':      break_color,
                'break_price':             break_price,
                'break_time':              event_day.index[break_bar_idx],
                'fwd_15m':                 fwd.get('fwd_15min'),
                'fwd_30m':                 fwd.get('fwd_30min'),
                'fwd_1hr':                 fwd.get('fwd_1hr'),
                'fwd_2hr':                 fwd.get('fwd_2hr'),
                'fwd_eod':                 fwd.get('fwd_EOD'),
                'max_adverse_excursion':   mae,
                'max_favorable_excursion': mfe,
            })

        except Exception:
            continue

    return pd.DataFrame(break_events), pd.DataFrame(orb_events)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — PRIMARY ANALYSIS: CANDLE COLOR VS FORWARD RETURNS
# ─────────────────────────────────────────────────────────────────────────────

def print_primary_analysis(broken: pd.DataFrame) -> pd.DataFrame:
    sep = '=' * 70
    print(f"\n{sep}")
    print("PRIMARY ANALYSIS: Forward Returns by Candle Color at Round Number Break")
    print(sep)

    color_stats_rows: list[dict] = []

    for color in ['CYAN', 'GREEN', 'GRAY', 'RED']:
        group = broken[broken['break_candle_color'] == color]
        n = len(group)
        if n == 0:
            continue

        print(f"\n--- {color} CANDLES (n={n}) ---")
        for col, label in [('fwd_15m', '15min'), ('fwd_30m', '30min'),
                             ('fwd_1hr', '1hr'),  ('fwd_2hr', '2hr'), ('fwd_eod', 'EOD')]:
            vals = group[col].dropna()
            if len(vals) == 0:
                continue
            win_rate = (vals > 0).mean() * 100
            avg_ret  = vals.mean()  * 100
            med_ret  = vals.median() * 100
            print(f"  {label:>6s}: Avg {avg_ret:+.2f}% | Med {med_ret:+.2f}% "
                  f"| Win Rate {win_rate:.1f}% | n={len(vals)}")
            color_stats_rows.append({
                'candle_color': color,
                'window':       label,
                'avg_return':   avg_ret,
                'win_rate':     win_rate,
                'n':            len(vals),
            })

        mae_vals = group['max_adverse_excursion'].dropna()
        if len(mae_vals):
            print(f"  MAE: Avg {mae_vals.mean()*100:.2f}% worst pullback | "
                  f"Med {mae_vals.median()*100:.2f}%")

    # Baseline — all breaks
    print(f"\n--- ALL BREAKS COMBINED (n={len(broken)}) ---")
    for col, label in [('fwd_15m', '15min'), ('fwd_30m', '30min'),
                         ('fwd_1hr', '1hr'),  ('fwd_2hr', '2hr'), ('fwd_eod', 'EOD')]:
        vals = broken[col].dropna()
        if len(vals) == 0:
            continue
        win_rate = (vals > 0).mean() * 100
        avg_ret  = vals.mean()  * 100
        med_ret  = vals.median() * 100
        print(f"  {label:>6s}: Avg {avg_ret:+.2f}% | Med {med_ret:+.2f}% "
              f"| Win Rate {win_rate:.1f}% | n={len(vals)}")
        color_stats_rows.append({
            'candle_color': 'ALL',
            'window':       label,
            'avg_return':   avg_ret,
            'win_rate':     win_rate,
            'n':            len(vals),
        })

    mae_all = broken['max_adverse_excursion'].dropna()
    if len(mae_all):
        print(f"  MAE: Avg {mae_all.mean()*100:.2f}% worst pullback | "
              f"Med {mae_all.median()*100:.2f}%")

    return pd.DataFrame(color_stats_rows)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — SECONDARY ANALYSIS: ORB LOW INTEGRITY
# ─────────────────────────────────────────────────────────────────────────────

def print_orb_analysis(orb_df: pd.DataFrame) -> None:
    sep = '=' * 70
    print(f"\n{sep}")
    print("SECONDARY ANALYSIS: Opening Range (First 5min Bar) Low Integrity")
    print(sep)

    n_total  = len(orb_df)
    n_broken = int(orb_df['orb_low_broken'].sum())
    n_held   = n_total - n_broken
    print(f"\nTotal gap days analyzed:          {n_total}")
    print(f"ORB Low broken during session:    {n_broken} ({n_broken / n_total * 100:.1f}%)")
    print(f"ORB Low HELD during session:      {n_held}  ({n_held / n_total * 100:.1f}%)")

    print()
    for color in ['CYAN', 'GREEN', 'GRAY', 'RED']:
        group = orb_df[orb_df['orb_candle_color'] == color]
        n = len(group)
        if n == 0:
            continue
        held_pct = (~group['orb_low_broken']).mean() * 100
        avg_eod  = group['orb_break_return_eod'].mean() * 100
        print(f"  {color:>5s} Opening Bar (n={n}):")
        print(f"    ORB Low Held:                  {held_pct:.1f}%")
        print(f"    Avg EOD Return from ORB High:  {avg_eod:+.2f}%")

    print("\nORB Low Integrity by Gap Size:")
    for low, high, label in [
        (0.05, 0.08, '5–8%'),
        (0.08, 0.12, '8–12%'),
        (0.12, 0.20, '12–20%'),
        (0.20, 1.00, '20%+'),
    ]:
        group = orb_df[(orb_df['gap_pct'] >= low) & (orb_df['gap_pct'] < high)]
        n = len(group)
        if n == 0:
            continue
        held_pct = (~group['orb_low_broken']).mean() * 100
        print(f"  Gap {label}: ORB Low Held {held_pct:.1f}% (n={n})")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — BREAKOUT TIMING ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def print_timing_analysis(broken: pd.DataFrame) -> None:
    sep = '=' * 70
    print(f"\n{sep}")
    print("TIMING ANALYSIS: When Does the Round Number Break Occur?")
    print(sep)

    timed = broken[broken['break_bar_idx'].notna()].copy()
    timed['break_bar_idx'] = timed['break_bar_idx'].astype(int)
    timed['break_timing']  = timed['break_bar_idx'].apply(classify_timing)

    for timing in ['FIRST_30MIN', '30_TO_60MIN', '1HR_TO_2HR', 'AFTER_2HR']:
        group    = timed[timed['break_timing'] == timing]
        n        = len(group)
        if n == 0:
            continue
        eod_vals = group['fwd_eod'].dropna()
        win_rate = (eod_vals > 0).mean() * 100 if len(eod_vals) > 0 else 0
        avg_ret  = eod_vals.mean() * 100        if len(eod_vals) > 0 else 0
        print(f"\n  {timing} (n={n}):")
        print(f"    EOD Return: Avg {avg_ret:+.2f}% | Win Rate {win_rate:.1f}%")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — SAVE OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────

def save_outputs(break_df: pd.DataFrame, orb_df: pd.DataFrame,
                 color_stats_df: pd.DataFrame) -> None:
    break_df.to_csv(
        os.path.join(OUTPUT_DIR, 'round_number_break_events.csv'), index=False
    )
    orb_df.to_csv(
        os.path.join(OUTPUT_DIR, 'orb_integrity_events.csv'), index=False
    )
    color_stats_df.to_csv(
        os.path.join(OUTPUT_DIR, 'candle_color_vs_returns.csv'), index=False
    )
    print(f"\n✅ Outputs saved to {OUTPUT_DIR}")


# ─────────────────────────────────────────────────────────────────────────────
# INTERPRETATION GUIDE
# ─────────────────────────────────────────────────────────────────────────────

INTERPRETATION = """
╔══════════════════════════════════════════════════════════════════════╗
║                     INTERPRETATION GUIDE                            ║
╠══════════════════════════════════════════════════════════════════════╣
║ If GRAY breaks ≈ CYAN breaks in forward returns:                    ║
║   → Candle color is NOISE on catalyst gap days                      ║
║   → The structural break IS the signal. Don't wait for cyan.        ║
║   → NEW RULE: On 5%+ gap days, round number break = entry.          ║
║                                                                      ║
║ If CYAN breaks significantly outperform GRAY:                        ║
║   → Momentum confirmation has value on gap days                     ║
║   → Waiting for cyan is justified (costs some entry price)          ║
║   → REFINE: Size smaller on gray, full size on cyan.                ║
║                                                                      ║
║ If ORB Low holds >75% on 5%+ gap days:                              ║
║   → ORB break entry + stop below ORB low = high-probability setup   ║
║   → Cutting weakness WITHIN the ORB range is premature              ║
╚══════════════════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("GAP + ROUND NUMBER BREAK + CANDLE COLOR STUDY")
    print(f"Universe: {len(UNIVERSE)} tickers | {START_DATE} → {END_DATE}")
    print("=" * 70)

    # Step 1 — identify gap days (or load cached CSV)
    gap_csv = os.path.join(OUTPUT_DIR, 'gap_events_raw.csv')
    if os.path.exists(gap_csv):
        print(f"Loading cached gap events from {gap_csv}")
        gap_df = pd.read_csv(gap_csv, parse_dates=['date'])
        print(f"  Loaded {len(gap_df)} events across {gap_df['ticker'].nunique()} tickers")
    else:
        gap_df = collect_gap_events(UNIVERSE)
        if gap_df.empty:
            print("No gap events found. Check API connectivity and date range.")
            return
        gap_df.to_csv(gap_csv, index=False)
        print(f"  (gap_events_raw.csv saved — {len(gap_df)} rows)")

    # Step 2 — intraday analysis
    print(f"\nAnalyzing {len(gap_df)} gap events (intraday + TrendStrength)...")
    break_df, orb_df = analyze_gap_events(gap_df)

    broken = break_df[break_df['level_broken'] == True].copy()

    print(f"\n=== ROUND NUMBER BREAK SUMMARY ===")
    print(f"Total gap events analyzed:  {len(gap_df)}")
    print(f"Round number broken:        {len(broken)}")
    print(f"Round number NOT broken:    {(~break_df['level_broken']).sum()}")

    # Step 3 — primary: candle color vs forward returns
    color_stats_df = print_primary_analysis(broken)

    # Step 4 — secondary: ORB integrity
    if not orb_df.empty:
        print_orb_analysis(orb_df)

    # Step 5 — timing
    if not broken.empty:
        print_timing_analysis(broken)

    # Step 6 — save
    save_outputs(break_df, orb_df, color_stats_df)

    print(INTERPRETATION)


if __name__ == '__main__':
    main()

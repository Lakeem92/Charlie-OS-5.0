# -*- coding: utf-8 -*-
"""
===================================================================
SUPPLEMENT: TS Line Slope Filter on Reverse FT Events
===================================================================
Answers: Of the high-WR reverse FT events, how many had the TrendStrength
line RISING vs FALLING at the time the reverse FT fired? Splits win rates
by TS slope direction so the indicator knows which reversals are tradeable.

Writes: outputs/supplement_ts_slope.csv (per-event with cs at FT bar)
        outputs/table5_updated_with_ts_slope.csv (summary)
===================================================================
"""

import sys, os, time
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import timedelta
from collections import defaultdict
from pathlib import Path

from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles

# ===============================================================
# CONFIG
# ===============================================================

STUDY_DIR   = Path(__file__).parent
OUTPUTS_DIR = STUDY_DIR / "outputs"
EVENT_CACHE = OUTPUTS_DIR / "all_events_with_cs.csv"
SLOPE_CACHE = OUTPUTS_DIR / "supplement_ts_slope.csv"

CHUNK_DAYS     = 120
SESSION_OPEN   = "09:30"
SESSION_CLOSE  = "16:00"
SLOPE_LOOKBACK = 5   # bars to look back for slope computation
FT_ATR_MULT    = 0.40


def normalise_cols(df):
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if lc == 'open':    rename[c] = 'Open'
        elif lc == 'high':  rename[c] = 'High'
        elif lc == 'low':   rename[c] = 'Low'
        elif lc == 'close': rename[c] = 'Close'
        elif lc in ('volume', 'vol'): rename[c] = 'Volume'
    return df.rename(columns=rename)


def to_eastern(df):
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(idx)
    if idx.tz is None:
        idx = idx.tz_localize('UTC')
    df = df.copy()
    df.index = idx.tz_convert('US/Eastern')
    return df


def classify_slope(cs_at_ft, cs_prior):
    """Classify TS line slope at FT trigger time."""
    if np.isnan(cs_at_ft) or np.isnan(cs_prior):
        return 'UNKNOWN'
    delta = cs_at_ft - cs_prior
    if delta > 10:
        return 'TS_RISING'
    elif delta < -10:
        return 'TS_FALLING'
    return 'TS_FLAT'


def classify_ts_level(cs_val):
    """Classify TS line level at FT trigger time."""
    if np.isnan(cs_val):
        return 'UNKNOWN'
    if cs_val >= 40:
        return 'BULLISH'
    elif cs_val >= -15:
        return 'NEUTRAL'
    return 'BEARISH'


def safe_flag(n):
    if n >= 20: return ''
    if n >= 10: return ' ⚠️LOW'
    return ' ❌INSUFF'


# ===============================================================
# MAIN
# ===============================================================

def main():
    print("=" * 70)
    print("SUPPLEMENT: TS Slope at Reverse FT Trigger")
    print("=" * 70)

    if SLOPE_CACHE.exists():
        print(f"  Cache exists: {SLOPE_CACHE}")
        print("  Loading from cache — skipping API calls.")
        result_df = pd.read_csv(SLOPE_CACHE)
        run_slope_analysis(result_df)
        return

    if not EVENT_CACHE.exists():
        raise FileNotFoundError(f"Event cache not found: {EVENT_CACHE}")

    events = pd.read_csv(EVENT_CACHE)
    rev_events = events[events['reverse_ft_fired'] == True].copy()
    print(f"  Total reverse FT events: {len(rev_events)}")
    print(f"  Unique tickers: {rev_events['ticker'].nunique()}")

    # Group by ticker
    events_by_ticker = defaultdict(list)
    for _, row in rev_events.iterrows():
        events_by_ticker[row['ticker']].append(row.to_dict())

    tsc = TrendStrengthCandles()
    results = []
    tickers_ok = 0
    tickers_fail = 0
    total_tickers = len(events_by_ticker)
    t0 = time.time()

    for i, (ticker, ticker_events) in enumerate(sorted(events_by_ticker.items())):
        if (i + 1) % 25 == 0 or (i + 1) == total_tickers:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total_tickers - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{total_tickers}] {ticker:6s} | "
                  f"{len(results)} events | "
                  f"{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining")

        event_dates = [pd.Timestamp(e['date']).tz_localize(None) for e in ticker_events]
        min_dt = min(event_dates) - timedelta(days=30)
        max_dt = max(event_dates) + timedelta(days=1)

        # Pull 5-min data in chunks
        chunks = []
        cursor = min_dt
        while cursor <= max_dt:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), max_dt)
            chunks.append((cursor.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
            cursor = chunk_end + timedelta(days=1)

        ticker_frames = []
        for start_str, end_str in chunks:
            try:
                intraday = DataRouter.get_price_data(
                    ticker, start_str, end_date=end_str,
                    timeframe='5min', fallback=False
                )
                if intraday is not None and len(intraday) > 0:
                    intraday = intraday.sort_index()
                    ticker_frames.append(intraday)
            except Exception:
                continue

        if not ticker_frames:
            tickers_fail += 1
            continue

        combined = pd.concat(ticker_frames).sort_index()
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = normalise_cols(combined)

        required = {'Open', 'High', 'Low', 'Close'}
        if not required.issubset(combined.columns):
            tickers_fail += 1
            continue

        combined = combined[combined['Close'].notna() & (combined['Close'] > 0)].copy()
        if len(combined) < 300:
            tickers_fail += 1
            continue

        try:
            df_cs = tsc.compute(combined)
        except Exception:
            tickers_fail += 1
            continue

        try:
            df_et = to_eastern(df_cs)
        except Exception:
            tickers_fail += 1
            continue

        tickers_ok += 1

        for ev in ticker_events:
            try:
                event_date = pd.Timestamp(ev['date']).tz_localize(None).date()
                day_bars = df_et[df_et.index.date == event_date]
                if len(day_bars) < 5:
                    continue

                session = day_bars.between_time(SESSION_OPEN, SESSION_CLOSE)
                if len(session) < 5:
                    continue

                session_open_time = session.index[0]
                ft_minutes = ev['reverse_ft_minutes']
                if np.isnan(ft_minutes):
                    continue

                # Find the bar closest to when reverse FT fired
                ft_time = session_open_time + pd.Timedelta(minutes=ft_minutes)
                # Get the bar index closest to (but not after) ft_time
                session_times = session.index
                ft_bar_mask = session_times <= ft_time
                if not ft_bar_mask.any():
                    continue

                ft_bar_idx = session_times[ft_bar_mask][-1]
                ft_bar_pos = session.index.get_loc(ft_bar_idx)

                # CS at FT bar
                cs_at_ft = float(session.iloc[ft_bar_pos]['cs']) \
                    if 'cs' in session.columns and not pd.isna(session.iloc[ft_bar_pos]['cs']) \
                    else np.nan

                # CS at bar-1 (session open)
                cs_bar1 = float(session.iloc[0]['cs']) \
                    if 'cs' in session.columns and not pd.isna(session.iloc[0]['cs']) \
                    else np.nan

                # CS slope: compare FT bar to SLOPE_LOOKBACK bars earlier
                cs_prior = np.nan
                if ft_bar_pos >= SLOPE_LOOKBACK:
                    prior_val = session.iloc[ft_bar_pos - SLOPE_LOOKBACK]['cs']
                    if not pd.isna(prior_val):
                        cs_prior = float(prior_val)

                slope = classify_slope(cs_at_ft, cs_prior)
                ts_level = classify_ts_level(cs_at_ft)

                # What bar is the FT bar (number from session open)
                ft_bar_number = ft_bar_pos

                # Candle at FT bar — is it bullish/bearish/neutral?
                ft_bar = session.iloc[ft_bar_pos]
                ft_o, ft_c = ft_bar['Open'], ft_bar['Close']
                ft_h, ft_l = ft_bar['High'], ft_bar['Low']
                ft_rng = ft_h - ft_l
                if ft_rng > 0:
                    ft_body_pct = abs(ft_c - ft_o) / ft_rng
                    if ft_body_pct <= 0.40:
                        ft_candle = 'NEUTRAL'
                    elif ft_c > ft_o:
                        ft_candle = 'BULLISH'
                    else:
                        ft_candle = 'BEARISH'
                else:
                    ft_candle = 'NEUTRAL'

                results.append({
                    'ticker':           ev['ticker'],
                    'date':             ev['date'],
                    'direction':        ev['direction'],
                    'gap_bucket':       ev['gap_bucket'],
                    'candle_tier':      ev['candle_tier'],
                    'win':              ev['win'],
                    'eod_return':       ev['eod_return'],
                    'hod_pct':          ev['hod_pct'],
                    'lod_pct':          ev['lod_pct'],
                    'hod_atr':          ev['hod_atr'],
                    'lod_atr':          ev['lod_atr'],
                    'reverse_ft_minutes': ft_minutes,
                    'cs_bar1':          round(cs_bar1, 2) if not np.isnan(cs_bar1) else np.nan,
                    'cs_at_ft':         round(cs_at_ft, 2) if not np.isnan(cs_at_ft) else np.nan,
                    'cs_prior':         round(cs_prior, 2) if not np.isnan(cs_prior) else np.nan,
                    'cs_slope_raw':     round(cs_at_ft - cs_prior, 2) if not (np.isnan(cs_at_ft) or np.isnan(cs_prior)) else np.nan,
                    'ts_slope':         slope,
                    'ts_level_at_ft':   ts_level,
                    'ft_bar_number':    ft_bar_number,
                    'ft_bar_candle':    ft_candle,
                })

            except Exception:
                continue

    elapsed = time.time() - t0
    print(f"\nProcessing complete in {elapsed:.0f}s")
    print(f"  Tickers OK: {tickers_ok} | Tickers fail: {tickers_fail}")
    print(f"  Events with slope data: {len(results)}")

    result_df = pd.DataFrame(results)
    result_df.to_csv(SLOPE_CACHE, index=False)
    print(f"  Saved: {SLOPE_CACHE}")

    run_slope_analysis(result_df)


def run_slope_analysis(df):
    """Generate the split tables by TS slope."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Reverse FT Win Rates by TS Slope at Trigger")
    print("=" * 70)

    tables = {}

    # ──────────────────────────────────────────────────────────
    # TABLE A: Gap-Down Bearish Bar-1 Reversed — by TS Slope
    # ──────────────────────────────────────────────────────────
    for direction, dir_label in [('GAP_DN', 'Gap-Down'), ('GAP_UP', 'Gap-Up')]:
        sub = df[df['direction'] == direction]

        # Bearish bar-1 reversals
        bearish_rev = sub[sub['candle_tier'].isin(['BEARISH', 'MAX_BEARISH'])]
        bullish_rev = sub[sub['candle_tier'].isin(['BULLISH', 'MAX_BULLISH'])]

        for group_label, group_df in [('BEARISH_REVERSED', bearish_rev),
                                       ('BULLISH_REVERSED', bullish_rev)]:
            if len(group_df) == 0:
                continue

            key = f"{dir_label}_{group_label}"
            print(f"\n  {key} (n={len(group_df)})")

            rows = []
            for slope in ['TS_RISING', 'TS_FLAT', 'TS_FALLING', 'UNKNOWN']:
                s = group_df[group_df['ts_slope'] == slope]
                if len(s) == 0:
                    continue
                n = len(s)
                rows.append({
                    'group':            key,
                    'ts_slope':         slope,
                    'n':                n,
                    'flag':             safe_flag(n),
                    'win_rate':         round(s['win'].mean() * 100, 1),
                    'avg_eod_return':   round(s['eod_return'].mean() * 100, 3),
                    'avg_hod_pct':      round(s['hod_pct'].mean() * 100, 3) if 'hod_pct' in s else np.nan,
                    'avg_lod_pct':      round(s['lod_pct'].mean() * 100, 3) if 'lod_pct' in s else np.nan,
                    'avg_hod_atr':      round(s['hod_atr'].mean(), 3),
                    'avg_lod_atr':      round(s['lod_atr'].mean(), 3),
                    'avg_cs_at_ft':     round(s['cs_at_ft'].mean(), 1),
                    'avg_cs_slope_raw': round(s['cs_slope_raw'].mean(), 1),
                    'med_ft_minutes':   round(s['reverse_ft_minutes'].median(), 0),
                })
                print(f"    {slope:12s} | n={n:4d}{safe_flag(n)} | "
                      f"WR={rows[-1]['win_rate']:.1f}% | "
                      f"EOD={rows[-1]['avg_eod_return']:+.3f}% | "
                      f"cs@FT={rows[-1]['avg_cs_at_ft']:.1f}")

            tables[key] = pd.DataFrame(rows)

    # Also split by TS LEVEL at FT time (bullish / neutral / bearish territory)
    print("\n" + "-" * 70)
    print("  BY TS LEVEL AT FT TRIGGER:")
    print("-" * 70)

    for direction, dir_label in [('GAP_DN', 'Gap-Down'), ('GAP_UP', 'Gap-Up')]:
        sub = df[df['direction'] == direction]
        bearish_rev = sub[sub['candle_tier'].isin(['BEARISH', 'MAX_BEARISH'])]
        bullish_rev = sub[sub['candle_tier'].isin(['BULLISH', 'MAX_BULLISH'])]

        for group_label, group_df in [('BEARISH_REVERSED', bearish_rev),
                                       ('BULLISH_REVERSED', bullish_rev)]:
            if len(group_df) == 0:
                continue

            key = f"{dir_label}_{group_label}_by_level"
            print(f"\n  {dir_label} {group_label} by TS Level (n={len(group_df)})")

            rows = []
            for level in ['BULLISH', 'NEUTRAL', 'BEARISH', 'UNKNOWN']:
                s = group_df[group_df['ts_level_at_ft'] == level]
                if len(s) == 0:
                    continue
                n = len(s)
                rows.append({
                    'group':            f"{dir_label}_{group_label}",
                    'ts_level':         level,
                    'n':                n,
                    'flag':             safe_flag(n),
                    'win_rate':         round(s['win'].mean() * 100, 1),
                    'avg_eod_return':   round(s['eod_return'].mean() * 100, 3),
                    'avg_cs_at_ft':     round(s['cs_at_ft'].mean(), 1),
                    'med_ft_minutes':   round(s['reverse_ft_minutes'].median(), 0),
                })
                print(f"    {level:12s} | n={n:4d}{safe_flag(n)} | "
                      f"WR={rows[-1]['win_rate']:.1f}% | "
                      f"cs@FT={rows[-1]['avg_cs_at_ft']:.1f}")

            tables[key] = pd.DataFrame(rows)

    # Combine by slope + candle at FT bar
    print("\n" + "-" * 70)
    print("  TRADEABLE FILTER: TS_RISING/FLAT + FT bar bullish/neutral")
    print("-" * 70)

    for direction, dir_label in [('GAP_DN', 'Gap-Down'), ('GAP_UP', 'Gap-Up')]:
        sub = df[df['direction'] == direction]
        bearish_rev = sub[sub['candle_tier'].isin(['BEARISH', 'MAX_BEARISH'])]

        if len(bearish_rev) == 0:
            continue

        if direction == 'GAP_DN':
            # Gap-down bearish bar-1 reversed = LONG setup
            # Tradeable = TS rising/flat + FT bar is bullish or neutral
            tradeable = bearish_rev[
                (bearish_rev['ts_slope'].isin(['TS_RISING', 'TS_FLAT'])) &
                (bearish_rev['ft_bar_candle'].isin(['BULLISH', 'NEUTRAL']))
            ]
            not_tradeable = bearish_rev[
                ~(
                    (bearish_rev['ts_slope'].isin(['TS_RISING', 'TS_FLAT'])) &
                    (bearish_rev['ft_bar_candle'].isin(['BULLISH', 'NEUTRAL']))
                )
            ]
        else:
            # Gap-up bearish bar-1 reversed = NOT the long setup, it's a continuation
            # Tradeable filter for gap-up bullish reversed (short):
            # TS falling/flat + FT bar bearish/neutral
            bullish_rev = sub[sub['candle_tier'].isin(['BULLISH', 'MAX_BULLISH'])]
            if len(bullish_rev) == 0:
                continue
            tradeable = bullish_rev[
                (bullish_rev['ts_slope'].isin(['TS_FALLING', 'TS_FLAT'])) &
                (bullish_rev['ft_bar_candle'].isin(['BEARISH', 'NEUTRAL']))
            ]
            not_tradeable = bullish_rev[
                ~(
                    (bullish_rev['ts_slope'].isin(['TS_FALLING', 'TS_FLAT'])) &
                    (bullish_rev['ft_bar_candle'].isin(['BEARISH', 'NEUTRAL']))
                )
            ]

        for label, grp in [('TRADEABLE', tradeable), ('NOT_TRADEABLE', not_tradeable)]:
            n = len(grp)
            if n == 0:
                continue
            wr = round(grp['win'].mean() * 100, 1)
            eod = round(grp['eod_return'].mean() * 100, 3)
            print(f"  {dir_label} | {label:16s} | n={n:4d}{safe_flag(n)} | "
                  f"WR={wr:.1f}% | EOD={eod:+.3f}%")

    # Save all tables
    all_rows = []
    for key, tbl in tables.items():
        all_rows.append(tbl)
    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        out_path = OUTPUTS_DIR / 'table5_updated_with_ts_slope.csv'
        combined.to_csv(out_path, index=False)
        print(f"\n  Saved: {out_path}")

    # Save the full TRADEABLE filter summary
    print("\n" + "=" * 70)
    print("SUPPLEMENT COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()

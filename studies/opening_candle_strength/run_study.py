# -*- coding: utf-8 -*-
"""
===================================================================
STUDY: Opening Candle Strength × Gap Regime — Final ATR_MOOOVVVEE Layer
===================================================================
CORE QUESTIONS:
  1. Does a MAX BULLISH (cyan, cs>=70) bar-1 on gap-downs produce
     meaningfully different outcomes than REGULAR bullish / neutral / bearish?
  2. Which gap regimes (2-5%, 5-8%, 8-12%, 12%+) benefit most from max bull?
  3. When bar-1 is bearish but price still hits reverse FT (0.4×ATR opposite),
     what are avg HOD/LOD and win rate? (both directions)
  4. Full HOD/LOD profile for all 5 candle tiers — raw % AND ATR-normalized.
  5. Terminal regime summary for direct indicator integration.

CANDLE TIERS (5):
  MAX_BULLISH  : TrendStrength cs >= 70, body > 40%, close > open
  BULLISH      : cs < 70, body > 40%, close > open
  NEUTRAL      : body <= 40% of range
  BEARISH      : cs > -70, body > 40%, close < open
  MAX_BEARISH  : cs <= -70, body > 40%, close < open

DATA: Reuses gap event caches from sibling studies. Only new API calls
are 5-min intraday for TrendStrength computation.
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
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from shared.data_router import DataRouter
from shared.indicators.trend_strength_candles import TrendStrengthCandles

# ===============================================================
# CONFIGURATION
# ===============================================================

STUDY_DIR   = Path(__file__).parent
OUTPUTS_DIR = STUDY_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Sibling caches (daily gap events — no candle info, just gap metadata)
GAPUP_CACHE = Path(r'C:\QuantLab\Data_Lab\studies\gap_execution_blueprint\outputs\gap_events_cache.csv')
GAPDN_CACHE = Path(r'C:\QuantLab\Data_Lab\studies\gap_down_execution_blueprint\outputs\gap_down_events_cache.csv')

# Intermediate cache — if this exists, skip the entire API phase
EVENT_CACHE = OUTPUTS_DIR / "all_events_with_cs.csv"

GAP_THRESHOLD       = 0.02        # 2% minimum absolute gap
ATR_PERIOD          = 14
FT_ATR_MULT         = 0.40        # FT = open ± (ATR × 0.40)
BODY_RATIO_THRESH   = 0.40        # body > 40% of range = directional candle
CS_MAX_BULL_THRESH  =  70         # TrendStrength cyan threshold
CS_MAX_BEAR_THRESH  = -70         # TrendStrength magenta threshold
CHUNK_DAYS          = 120         # 5-min API chunk size

SESSION_OPEN  = "09:30"
SESSION_CLOSE = "16:00"


# ===============================================================
# HELPERS
# ===============================================================

def gap_bucket(abs_gap_pct):
    """Classify absolute gap % into regimes."""
    if abs_gap_pct >= 0.12:   return '12%+'
    if abs_gap_pct >= 0.08:   return '8-12%'
    if abs_gap_pct >= 0.05:   return '5-8%'
    return '2-5%'


def classify_candle_5tier(bar_row, cs_value):
    """
    Classify bar-1 into 5 tiers using body ratio + TrendStrength cs.
    bar_row: dict-like with Open, High, Low, Close
    cs_value: float, TrendStrength consensus score
    """
    o, h, l, c = bar_row['Open'], bar_row['High'], bar_row['Low'], bar_row['Close']
    rng = h - l
    if rng == 0:
        return 'NEUTRAL'

    body_pct = abs(c - o) / rng

    if body_pct <= BODY_RATIO_THRESH:
        return 'NEUTRAL'
    elif c > o:
        # Bullish candle — check if max
        if not np.isnan(cs_value) and cs_value >= CS_MAX_BULL_THRESH:
            return 'MAX_BULLISH'
        return 'BULLISH'
    else:
        # Bearish candle — check if max
        if not np.isnan(cs_value) and cs_value <= CS_MAX_BEAR_THRESH:
            return 'MAX_BEARISH'
        return 'BEARISH'


def normalise_cols(df):
    """Standardize column names to Open/High/Low/Close/Volume."""
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if lc == 'open':   rename[c] = 'Open'
        elif lc == 'high':  rename[c] = 'High'
        elif lc == 'low':   rename[c] = 'Low'
        elif lc == 'close': rename[c] = 'Close'
        elif lc in ('volume', 'vol'): rename[c] = 'Volume'
    return df.rename(columns=rename)


def to_eastern(df):
    """Convert index to US/Eastern."""
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(idx)
    if idx.tz is None:
        idx = idx.tz_localize('UTC')
    df = df.copy()
    df.index = idx.tz_convert('US/Eastern')
    return df


def safe_flag(n):
    """Return sample size flag."""
    if n >= 20: return ''
    if n >= 10: return ' ⚠️LOW'
    return ' ❌INSUFF'


# ===============================================================
# STEP 1: LOAD BASE GAP EVENTS FROM SIBLING CACHES
# ===============================================================

def load_gap_events():
    """Load gap-up and gap-down events from sibling study caches."""
    print("=" * 70)
    print("STEP 1: Loading gap events from sibling caches")
    print("=" * 70)

    if not GAPUP_CACHE.exists() or not GAPDN_CACHE.exists():
        raise FileNotFoundError(
            "Sibling study caches not found. Run gap_execution_blueprint and "
            "gap_down_execution_blueprint first."
        )

    gapup = pd.read_csv(GAPUP_CACHE)
    gapdn = pd.read_csv(GAPDN_CACHE)

    events = []

    for _, r in gapup.iterrows():
        events.append({
            'ticker':     r['ticker'],
            'date':       r['date'],
            'open_price': r['open_price'],
            'prev_close': r['prev_close'],
            'gap_pct':    r['gap_pct'],
            'atr':        r['atr'],
            'direction':  'GAP_UP',
        })

    for _, r in gapdn.iterrows():
        events.append({
            'ticker':     r['ticker'],
            'date':       r['date'],
            'open_price': r['open_price'],
            'prev_close': r['prev_close'],
            'gap_pct':    r['gap_pct'],
            'atr':        r['atr'],
            'direction':  'GAP_DN',
        })

    df = pd.DataFrame(events)
    df['abs_gap_pct'] = df['gap_pct'].abs()
    df['gap_bucket']  = df['abs_gap_pct'].apply(gap_bucket)

    print(f"  Gap-ups:  {(df['direction']=='GAP_UP').sum()}")
    print(f"  Gap-downs: {(df['direction']=='GAP_DN').sum()}")
    print(f"  Total:    {len(df)}")
    print(f"  Tickers:  {df['ticker'].nunique()}")
    return df


# ===============================================================
# STEP 2: PULL INTRADAY + COMPUTE TRENDSTRENGTH + EXTRACT METRICS
# ===============================================================

def process_all_events(gap_df):
    """
    For each event, pull 5-min intraday data, compute TrendStrength,
    classify bar-1, and extract session metrics.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Processing intraday data + TrendStrength + session metrics")
    print("=" * 70)

    events_by_ticker = defaultdict(list)
    for _, ev in gap_df.iterrows():
        events_by_ticker[ev['ticker']].append(ev.to_dict())

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
                  f"{len(results)} events processed | "
                  f"{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining")

        event_dates = [pd.Timestamp(e['date']).tz_localize(None) for e in ticker_events]
        min_dt = min(event_dates) - timedelta(days=30)  # 30-day warmup buffer
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

        # Compute TrendStrength on full series (warmup included)
        try:
            df_cs = tsc.compute(combined)
        except Exception:
            tickers_fail += 1
            continue

        # Convert to Eastern time
        try:
            df_et = to_eastern(df_cs)
        except Exception:
            tickers_fail += 1
            continue

        tickers_ok += 1

        # Process each event for this ticker
        for ev in ticker_events:
            try:
                event_date = pd.Timestamp(ev['date']).date()
                day_bars = df_et[df_et.index.date == event_date]
                if len(day_bars) < 5:
                    continue

                session = day_bars.between_time(SESSION_OPEN, SESSION_CLOSE)
                if len(session) < 5:
                    continue

                bar1 = session.iloc[0]
                cs_val = float(bar1['cs']) if 'cs' in bar1.index and not pd.isna(bar1['cs']) else np.nan
                candle_tier = classify_candle_5tier(bar1, cs_val)

                open_price = ev['open_price']
                atr = ev['atr']
                direction = ev['direction']

                # Session extremes
                session_high = session['High'].max()
                session_low  = session['Low'].min()
                eod_close    = session.iloc[-1]['Close']

                session_open_time = session.index[0]
                hod_idx = session['High'].idxmax()
                lod_idx = session['Low'].idxmin()
                hod_minutes = (hod_idx - session_open_time).total_seconds() / 60.0
                lod_minutes = (lod_idx - session_open_time).total_seconds() / 60.0

                # HOD/LOD as % from open and ATR-normalized
                hod_pct = (session_high - open_price) / open_price
                lod_pct = (open_price - session_low) / open_price
                hod_atr = (session_high - open_price) / atr if atr > 0 else np.nan
                lod_atr = (open_price - session_low) / atr if atr > 0 else np.nan

                # Win definition
                if direction == 'GAP_DN':
                    win = 1 if eod_close > open_price else 0       # rally from gap-down
                    eod_return = (eod_close - open_price) / open_price
                else:
                    win = 1 if eod_close < open_price else 0       # fade from gap-up
                    eod_return = (open_price - eod_close) / open_price

                # FT levels (in the GAP direction)
                if direction == 'GAP_DN':
                    ft_bounce = open_price + (atr * FT_ATR_MULT)   # upside FT (bounce)
                    ft_cont   = open_price - (atr * FT_ATR_MULT)   # downside FT (continuation)
                else:
                    ft_bounce = open_price - (atr * FT_ATR_MULT)   # downside FT (fade)
                    ft_cont   = open_price + (atr * FT_ATR_MULT)   # upside FT (continuation)

                # Check if REVERSE FT fired (opposite of bar-1 sentiment)
                # For bearish bar-1: did price hit the BOUNCE/UPSIDE FT?
                # For bullish bar-1: did price hit the FADE/DOWNSIDE FT?
                reverse_ft_fired = False
                reverse_ft_minutes = np.nan

                if candle_tier in ('BEARISH', 'MAX_BEARISH'):
                    # Bearish bar-1 -> check if price hit opposite (bounce) FT
                    if direction == 'GAP_DN':
                        # Gap-down, bearish bar-1, check upside FT
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] >= ft_bounce:
                                reverse_ft_fired = True
                                reverse_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break
                    else:
                        # Gap-up, bearish bar-1, check upside FT (continuation for gap-up)
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] >= ft_cont:
                                reverse_ft_fired = True
                                reverse_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break

                elif candle_tier in ('BULLISH', 'MAX_BULLISH'):
                    # Bullish bar-1 -> check if price hit opposite (fade) FT
                    if direction == 'GAP_UP':
                        # Gap-up, bullish bar-1, check downside FT
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] <= ft_bounce:
                                reverse_ft_fired = True
                                reverse_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break
                    else:
                        # Gap-down, bullish bar-1, check downside FT (continuation)
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] <= ft_cont:
                                reverse_ft_fired = True
                                reverse_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break

                # Standard FT (in the expected direction for the candle)
                std_ft_fired = False
                std_ft_minutes = np.nan

                if candle_tier in ('BULLISH', 'MAX_BULLISH'):
                    if direction == 'GAP_DN':
                        # Bullish on gap-down -> bounce FT (upside)
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] >= ft_bounce:
                                std_ft_fired = True
                                std_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break
                    else:
                        # Bullish on gap-up -> continuation FT (upside)
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] >= ft_cont:
                                std_ft_fired = True
                                std_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break

                elif candle_tier in ('BEARISH', 'MAX_BEARISH'):
                    if direction == 'GAP_UP':
                        # Bearish on gap-up -> fade FT (downside)
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] <= ft_bounce:
                                std_ft_fired = True
                                std_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break
                    else:
                        # Bearish on gap-down -> continuation FT (downside)
                        for j in range(len(session)):
                            if session.iloc[j]['Close'] <= ft_cont:
                                std_ft_fired = True
                                std_ft_minutes = (session.index[j] - session_open_time).total_seconds() / 60.0
                                break

                # HOD/LOD timing bucket
                def timing_bucket(minutes):
                    if minutes <= 5:   return 'AT_OPEN'
                    if minutes <= 30:  return 'FIRST_30MIN'
                    if minutes <= 60:  return 'FIRST_HOUR'
                    if minutes <= 120: return 'FIRST_2HR'
                    if minutes <= 300: return 'MID_SESSION'
                    return 'LAST_HOUR'

                results.append({
                    'ticker':             ev['ticker'],
                    'date':               ev['date'],
                    'direction':          direction,
                    'gap_pct':            ev['gap_pct'],
                    'abs_gap_pct':        abs(ev['gap_pct']),
                    'gap_bucket':         gap_bucket(abs(ev['gap_pct'])),
                    'atr':                atr,
                    'open_price':         open_price,
                    'prev_close':         ev['prev_close'],
                    'cs_score':           round(cs_val, 2) if not np.isnan(cs_val) else np.nan,
                    'candle_tier':        candle_tier,
                    'session_high':       round(session_high, 4),
                    'session_low':        round(session_low, 4),
                    'eod_close':          round(eod_close, 4),
                    'hod_pct':            round(hod_pct, 6),
                    'lod_pct':            round(lod_pct, 6),
                    'hod_atr':            round(hod_atr, 4) if not np.isnan(hod_atr) else np.nan,
                    'lod_atr':            round(lod_atr, 4) if not np.isnan(lod_atr) else np.nan,
                    'hod_minutes':        round(hod_minutes, 1),
                    'lod_minutes':        round(lod_minutes, 1),
                    'hod_timing_bucket':  timing_bucket(hod_minutes),
                    'lod_timing_bucket':  timing_bucket(lod_minutes),
                    'eod_return':         round(eod_return, 6),
                    'win':                win,
                    'std_ft_fired':       std_ft_fired,
                    'std_ft_minutes':     round(std_ft_minutes, 1) if not np.isnan(std_ft_minutes) else np.nan,
                    'reverse_ft_fired':   reverse_ft_fired,
                    'reverse_ft_minutes': round(reverse_ft_minutes, 1) if not np.isnan(reverse_ft_minutes) else np.nan,
                })

            except Exception:
                continue

    elapsed = time.time() - t0
    print(f"\nStep 2 complete in {elapsed:.0f}s")
    print(f"  Tickers OK: {tickers_ok} | Tickers fail: {tickers_fail}")
    print(f"  Events processed: {len(results)}")

    result_df = pd.DataFrame(results)
    result_df.to_csv(EVENT_CACHE, index=False)
    print(f"  Saved: {EVENT_CACHE}")
    return result_df


# ===============================================================
# STEP 3: ANALYSIS— ALL 7 TABLES
# ===============================================================

def run_analysis(df):
    """Generate all analysis tables from the event cache."""
    print("\n" + "=" * 70)
    print("STEP 3: Running analysis — 7 tables")
    print("=" * 70)

    # ─── TABLE 1: Gap-Down Candle Strength × Outcomes ─────────────
    print("\n  TABLE 1: Gap-Down × Candle Tier")
    gd = df[df['direction'] == 'GAP_DN'].copy()
    t1_rows = []
    for tier in ['MAX_BULLISH', 'BULLISH', 'NEUTRAL', 'BEARISH', 'MAX_BEARISH']:
        sub = gd[gd['candle_tier'] == tier]
        n = len(sub)
        if n == 0:
            continue
        t1_rows.append({
            'candle_tier':      tier,
            'n':                n,
            'win_rate':         round(sub['win'].mean() * 100, 1),
            'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
            'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
            'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
            'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
            'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
            'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
            'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
            'ft_fire_rate':     round(sub['std_ft_fired'].mean() * 100, 1),
        })
    t1 = pd.DataFrame(t1_rows)
    t1.to_csv(OUTPUTS_DIR / 'table1_gapdown_candle_outcomes.csv', index=False)
    print(f"    Saved table 1 ({len(t1)} rows)")

    # ─── TABLE 2: Gap-Up Candle Strength × Outcomes ───────────────
    print("  TABLE 2: Gap-Up × Candle Tier")
    gu = df[df['direction'] == 'GAP_UP'].copy()
    t2_rows = []
    for tier in ['MAX_BEARISH', 'BEARISH', 'NEUTRAL', 'BULLISH', 'MAX_BULLISH']:
        sub = gu[gu['candle_tier'] == tier]
        n = len(sub)
        if n == 0:
            continue
        t2_rows.append({
            'candle_tier':      tier,
            'n':                n,
            'win_rate':         round(sub['win'].mean() * 100, 1),
            'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
            'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
            'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
            'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
            'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
            'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
            'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
            'ft_fire_rate':     round(sub['std_ft_fired'].mean() * 100, 1),
        })
    t2 = pd.DataFrame(t2_rows)
    t2.to_csv(OUTPUTS_DIR / 'table2_gapup_candle_outcomes.csv', index=False)
    print(f"    Saved table 2 ({len(t2)} rows)")

    # ─── TABLE 3: Gap-Down Regime × Candle Cross-Tab ──────────────
    print("  TABLE 3: Gap-Down Regime × Candle Cross-Tab")
    t3_rows = []
    for bucket in ['2-5%', '5-8%', '8-12%', '12%+']:
        for tier in ['MAX_BULLISH', 'BULLISH', 'NEUTRAL', 'BEARISH', 'MAX_BEARISH']:
            sub = gd[(gd['gap_bucket'] == bucket) & (gd['candle_tier'] == tier)]
            n = len(sub)
            if n == 0:
                continue
            t3_rows.append({
                'gap_bucket':       bucket,
                'candle_tier':      tier,
                'n':                n,
                'flag':             safe_flag(n),
                'win_rate':         round(sub['win'].mean() * 100, 1),
                'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
                'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
                'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
                'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
                'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
                'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
                'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
                'ft_fire_rate':     round(sub['std_ft_fired'].mean() * 100, 1),
            })
    t3 = pd.DataFrame(t3_rows)
    t3.to_csv(OUTPUTS_DIR / 'table3_gapdown_regime_crosstab.csv', index=False)
    print(f"    Saved table 3 ({len(t3)} rows)")

    # ─── TABLE 4: Gap-Up Regime × Candle Cross-Tab ────────────────
    print("  TABLE 4: Gap-Up Regime × Candle Cross-Tab")
    t4_rows = []
    for bucket in ['2-5%', '5-8%', '8-12%', '12%+']:
        for tier in ['MAX_BEARISH', 'BEARISH', 'NEUTRAL', 'BULLISH', 'MAX_BULLISH']:
            sub = gu[(gu['gap_bucket'] == bucket) & (gu['candle_tier'] == tier)]
            n = len(sub)
            if n == 0:
                continue
            t4_rows.append({
                'gap_bucket':       bucket,
                'candle_tier':      tier,
                'n':                n,
                'flag':             safe_flag(n),
                'win_rate':         round(sub['win'].mean() * 100, 1),
                'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
                'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
                'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
                'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
                'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
                'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
                'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
                'ft_fire_rate':     round(sub['std_ft_fired'].mean() * 100, 1),
            })
    t4 = pd.DataFrame(t4_rows)
    t4.to_csv(OUTPUTS_DIR / 'table4_gapup_regime_crosstab.csv', index=False)
    print(f"    Saved table 4 ({len(t4)} rows)")

    # ─── TABLE 5: Bearish Bar-1 Reverse FT Analysis ──────────────
    print("  TABLE 5: Bearish/Bullish Bar-1 Reverse FT Analysis")
    t5_rows = []

    # Part A: Bearish bar-1 that hits reverse (opposite) FT
    for direction in ['GAP_DN', 'GAP_UP']:
        sub_dir = df[df['direction'] == direction]

        # Bearish bar-1 events in this direction
        bearish = sub_dir[sub_dir['candle_tier'].isin(['BEARISH', 'MAX_BEARISH'])]
        bear_rev = bearish[bearish['reverse_ft_fired'] == True]
        bear_no_rev = bearish[bearish['reverse_ft_fired'] == False]

        for label, sub in [('BEARISH_REVERSED', bear_rev), ('BEARISH_NOT_REVERSED', bear_no_rev)]:
            n = len(sub)
            if n == 0:
                continue
            t5_rows.append({
                'direction':        direction,
                'group':            label,
                'n':                n,
                'flag':             safe_flag(n),
                'win_rate':         round(sub['win'].mean() * 100, 1),
                'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
                'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
                'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
                'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
                'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
                'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
                'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
                'med_ft_minutes':   round(sub['reverse_ft_minutes'].median(), 0) if label.endswith('REVERSED') else np.nan,
            })

        # Bullish bar-1 events in this direction
        bullish = sub_dir[sub_dir['candle_tier'].isin(['BULLISH', 'MAX_BULLISH'])]
        bull_rev = bullish[bullish['reverse_ft_fired'] == True]
        bull_no_rev = bullish[bullish['reverse_ft_fired'] == False]

        for label, sub in [('BULLISH_REVERSED', bull_rev), ('BULLISH_NOT_REVERSED', bull_no_rev)]:
            n = len(sub)
            if n == 0:
                continue
            t5_rows.append({
                'direction':        direction,
                'group':            label,
                'n':                n,
                'flag':             safe_flag(n),
                'win_rate':         round(sub['win'].mean() * 100, 1),
                'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
                'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
                'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
                'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
                'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
                'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
                'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
                'med_ft_minutes':   round(sub['reverse_ft_minutes'].median(), 0) if label.endswith('REVERSED') else np.nan,
            })

    t5 = pd.DataFrame(t5_rows)
    t5.to_csv(OUTPUTS_DIR / 'table5_reverse_ft_analysis.csv', index=False)
    print(f"    Saved table 5 ({len(t5)} rows)")

    # ─── TABLE 6: HOD/LOD Timing Profile by Candle Type ──────────
    print("  TABLE 6: HOD/LOD Timing Profile by Candle Tier")
    timing_buckets = ['AT_OPEN', 'FIRST_30MIN', 'FIRST_HOUR', 'FIRST_2HR', 'MID_SESSION', 'LAST_HOUR']
    t6_rows = []

    for direction in ['GAP_DN', 'GAP_UP']:
        sub_dir = df[df['direction'] == direction]
        for tier in ['MAX_BULLISH', 'BULLISH', 'NEUTRAL', 'BEARISH', 'MAX_BEARISH']:
            sub = sub_dir[sub_dir['candle_tier'] == tier]
            n = len(sub)
            if n == 0:
                continue

            # HOD timing distribution
            hod_dist = sub['hod_timing_bucket'].value_counts(normalize=True)
            lod_dist = sub['lod_timing_bucket'].value_counts(normalize=True)

            row = {
                'direction':    direction,
                'candle_tier':  tier,
                'n':            n,
                'flag':         safe_flag(n),
            }
            for b in timing_buckets:
                row[f'hod_{b}'] = round(hod_dist.get(b, 0) * 100, 1)
                row[f'lod_{b}'] = round(lod_dist.get(b, 0) * 100, 1)
            t6_rows.append(row)

    t6 = pd.DataFrame(t6_rows)
    t6.to_csv(OUTPUTS_DIR / 'table6_hod_lod_timing_profile.csv', index=False)
    print(f"    Saved table 6 ({len(t6)} rows)")

    # ─── TABLE 7: Ultimate Regime Summary ─────────────────────────
    print("  TABLE 7: Ultimate Regime Summary (the indicator lookup table)")
    t7_rows = []
    for direction in ['GAP_DN', 'GAP_UP']:
        sub_dir = df[df['direction'] == direction]
        for bucket in ['2-5%', '5-8%', '8-12%', '12%+']:
            for tier in ['MAX_BULLISH', 'BULLISH', 'NEUTRAL', 'BEARISH', 'MAX_BEARISH']:
                sub = sub_dir[(sub_dir['gap_bucket'] == bucket) & (sub_dir['candle_tier'] == tier)]
                n = len(sub)
                if n == 0:
                    continue
                t7_rows.append({
                    'direction':        direction,
                    'gap_bucket':       bucket,
                    'candle_tier':      tier,
                    'n':                n,
                    'flag':             safe_flag(n),
                    'win_rate':         round(sub['win'].mean() * 100, 1),
                    'avg_eod_return':   round(sub['eod_return'].mean() * 100, 3),
                    'avg_hod_pct':      round(sub['hod_pct'].mean() * 100, 3),
                    'avg_lod_pct':      round(sub['lod_pct'].mean() * 100, 3),
                    'avg_hod_atr':      round(sub['hod_atr'].mean(), 3),
                    'avg_lod_atr':      round(sub['lod_atr'].mean(), 3),
                    'med_hod_minutes':  round(sub['hod_minutes'].median(), 0),
                    'med_lod_minutes':  round(sub['lod_minutes'].median(), 0),
                    'ft_fire_rate':     round(sub['std_ft_fired'].mean() * 100, 1),
                    'rev_ft_fire_rate': round(sub['reverse_ft_fired'].mean() * 100, 1),
                })
    t7 = pd.DataFrame(t7_rows)
    t7.to_csv(OUTPUTS_DIR / 'table7_ultimate_regime_summary.csv', index=False)
    print(f"    Saved table 7 ({len(t7)} rows)")

    return {
        't1': t1, 't2': t2, 't3': t3, 't4': t4,
        't5': t5, 't6': t6, 't7': t7,
        'gap_down': gd, 'gap_up': gu, 'all': df,
    }


# ===============================================================
# STEP 4: GENERATE README.MD
# ===============================================================

def generate_readme(tables):
    """Generate the findings README.md."""
    print("\n" + "=" * 70)
    print("STEP 4: Generating README.md")
    print("=" * 70)

    t1, t2, t3, t4, t5, t6, t7 = (
        tables['t1'], tables['t2'], tables['t3'], tables['t4'],
        tables['t5'], tables['t6'], tables['t7'],
    )
    df = tables['all']
    gd = tables['gap_down']
    gu = tables['gap_up']

    lines = []
    def L(s=''):
        lines.append(s)

    L("# Opening Candle Strength × Gap Regime Study")
    L(f"**Generated:** {datetime.now():%Y-%m-%d %H:%M}")
    L(f"**Purpose:** Final data layer for ATR_MOOOVVVEE_INDICATOR rewrite")
    L()
    L("## Study Design")
    L()
    L("### Questions Answered")
    L("1. Does a MAX BULLISH (TrendStrength cs≥70) bar-1 on gap-downs produce better outcomes than regular bullish/neutral/bearish?")
    L("2. Which gap regimes (2-5%, 5-8%, 8-12%, 12%+) benefit most from max bullish opens?")
    L("3. When bar-1 is bearish but price still hits reverse FT (0.4×ATR), what are the HOD/LOD and win rates?")
    L("4. Full HOD/LOD profile for all 5 candle tiers — raw % AND ATR-normalized")
    L("5. Ultimate regime summary for direct indicator integration")
    L()
    L("### Methodology")
    L(f"- **Universe:** {df['ticker'].nunique()} tickers, {df['date'].nunique()} unique dates")
    L(f"- **Total events:** {len(df)} ({len(gd)} gap-downs, {len(gu)} gap-ups)")
    L(f"- **Period:** {df['date'].min()} to {df['date'].max()}")
    L("- **Gap threshold:** ≥2% absolute")
    L("- **Bar-1:** First 5-min candle of session (9:30-9:35 ET)")
    L("- **Candle tiers:** 5-tier classification using body ratio (>40%) + TrendStrength cs score")
    L("- **Win:** Close > Open for gap-downs (rally), Close < Open for gap-ups (fade)")
    L("- **FT threshold:** 0.40 × ATR14")
    L("- **HOD/LOD:** Both raw % from open AND ATR-normalized")
    L()
    L("### Candle Tier Definitions")
    L("| Tier | Criteria |")
    L("|------|----------|")
    L("| MAX_BULLISH | cs ≥ 70, body > 40%, close > open |")
    L("| BULLISH | cs < 70, body > 40%, close > open |")
    L("| NEUTRAL | body ≤ 40% of range (any cs) |")
    L("| BEARISH | cs > -70, body > 40%, close < open |")
    L("| MAX_BEARISH | cs ≤ -70, body > 40%, close < open |")
    L()

    # ─── TABLE 1 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 1: Gap-Down × Opening Candle Tier")
    L()
    L("**Question:** Does MAX_BULLISH bar-1 on gap-downs predict better bounce outcomes?")
    L()
    if not t1.empty:
        L("| Candle Tier | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT Fire% |")
        L("|-------------|---|----------|-------------|----------|----------|-----------|-----------|-------------|-------------|----------|")
        for _, r in t1.iterrows():
            sf = safe_flag(r['n'])
            L(f"| {r['candle_tier']}{sf} | {r['n']} | {r['win_rate']}% | {r['avg_eod_return']:+.3f}% | {r['avg_hod_pct']:.3f}% | {r['avg_lod_pct']:.3f}% | {r['avg_hod_atr']:.3f} | {r['avg_lod_atr']:.3f} | {r['med_hod_minutes']:.0f} | {r['med_lod_minutes']:.0f} | {r['ft_fire_rate']:.1f}% |")
        L()

        # Key insights
        max_bull = t1[t1['candle_tier'] == 'MAX_BULLISH']
        reg_bull = t1[t1['candle_tier'] == 'BULLISH']
        if not max_bull.empty and not reg_bull.empty:
            mb_wr = max_bull.iloc[0]['win_rate']
            rb_wr = reg_bull.iloc[0]['win_rate']
            diff = mb_wr - rb_wr
            L(f"**Key Insight:** MAX_BULLISH win rate = {mb_wr:.1f}% vs BULLISH = {rb_wr:.1f}% ({diff:+.1f} pp)")
            L()

    # ─── TABLE 2 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 2: Gap-Up × Opening Candle Tier")
    L()
    L("**Question:** Does MAX_BEARISH bar-1 on gap-ups predict better fade outcomes?")
    L()
    if not t2.empty:
        L("| Candle Tier | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT Fire% |")
        L("|-------------|---|----------|-------------|----------|----------|-----------|-----------|-------------|-------------|----------|")
        for _, r in t2.iterrows():
            sf = safe_flag(r['n'])
            L(f"| {r['candle_tier']}{sf} | {r['n']} | {r['win_rate']}% | {r['avg_eod_return']:+.3f}% | {r['avg_hod_pct']:.3f}% | {r['avg_lod_pct']:.3f}% | {r['avg_hod_atr']:.3f} | {r['avg_lod_atr']:.3f} | {r['med_hod_minutes']:.0f} | {r['med_lod_minutes']:.0f} | {r['ft_fire_rate']:.1f}% |")
        L()

        max_bear = t2[t2['candle_tier'] == 'MAX_BEARISH']
        reg_bear = t2[t2['candle_tier'] == 'BEARISH']
        if not max_bear.empty and not reg_bear.empty:
            mb_wr = max_bear.iloc[0]['win_rate']
            rb_wr = reg_bear.iloc[0]['win_rate']
            diff = mb_wr - rb_wr
            L(f"**Key Insight:** MAX_BEARISH win rate = {mb_wr:.1f}% vs BEARISH = {rb_wr:.1f}% ({diff:+.1f} pp)")
            L()

    # ─── TABLE 3 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 3: Gap-Down — Regime × Candle Cross-Tab")
    L()
    L("**Question:** In which gap regimes does MAX_BULLISH perform best?")
    L()
    if not t3.empty:
        for bucket in ['2-5%', '5-8%', '8-12%', '12%+']:
            sub = t3[t3['gap_bucket'] == bucket]
            if sub.empty:
                continue
            L(f"### Gap-Down {bucket}")
            L("| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |")
            L("|-------------|---|----------|-------------|-----------|-----------|----------|")
            for _, r in sub.iterrows():
                L(f"| {r['candle_tier']}{r['flag']} | {r['n']} | {r['win_rate']}% | {r['avg_eod_return']:+.3f}% | {r['avg_hod_atr']:.3f} | {r['avg_lod_atr']:.3f} | {r['ft_fire_rate']:.1f}% |")
            L()

    # ─── TABLE 4 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 4: Gap-Up — Regime × Candle Cross-Tab")
    L()
    L("**Question:** In which gap regimes does MAX_BEARISH perform best?")
    L()
    if not t4.empty:
        for bucket in ['2-5%', '5-8%', '8-12%', '12%+']:
            sub = t4[t4['gap_bucket'] == bucket]
            if sub.empty:
                continue
            L(f"### Gap-Up {bucket}")
            L("| Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | FT Fire% |")
            L("|-------------|---|----------|-------------|-----------|-----------|----------|")
            for _, r in sub.iterrows():
                L(f"| {r['candle_tier']}{r['flag']} | {r['n']} | {r['win_rate']}% | {r['avg_eod_return']:+.3f}% | {r['avg_hod_atr']:.3f} | {r['avg_lod_atr']:.3f} | {r['ft_fire_rate']:.1f}% |")
            L()

    # ─── TABLE 5 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 5: Bearish/Bullish Bar-1 Reverse FT Analysis")
    L()
    L("**Question:** When bar-1 is bearish but price still hits the OPPOSITE FT level (0.4×ATR), what happens?")
    L()
    if not t5.empty:
        for direction in ['GAP_DN', 'GAP_UP']:
            sub = t5[t5['direction'] == direction]
            if sub.empty:
                continue
            dir_label = "Gap-Down" if direction == 'GAP_DN' else "Gap-Up"
            L(f"### {dir_label}")
            L("| Group | n | Win Rate | Avg EOD Ret | Avg HOD% | Avg LOD% | HOD (ATR) | LOD (ATR) | Med FT Min |")
            L("|-------|---|----------|-------------|----------|----------|-----------|-----------|------------|")
            for _, r in sub.iterrows():
                ft_min = f"{r['med_ft_minutes']:.0f}" if not pd.isna(r['med_ft_minutes']) else "—"
                L(f"| {r['group']}{r['flag']} | {r['n']} | {r['win_rate']}% | {r['avg_eod_return']:+.3f}% | {r['avg_hod_pct']:.3f}% | {r['avg_lod_pct']:.3f}% | {r['avg_hod_atr']:.3f} | {r['avg_lod_atr']:.3f} | {ft_min} |")
            L()

    # ─── TABLE 6 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 6: HOD/LOD Timing Profile by Candle Tier")
    L()
    L("**Question:** When does the session high/low get set, by candle type?")
    L()
    timing_buckets = ['AT_OPEN', 'FIRST_30MIN', 'FIRST_HOUR', 'FIRST_2HR', 'MID_SESSION', 'LAST_HOUR']
    if not t6.empty:
        for direction in ['GAP_DN', 'GAP_UP']:
            sub = t6[t6['direction'] == direction]
            if sub.empty:
                continue
            dir_label = "Gap-Down" if direction == 'GAP_DN' else "Gap-Up"
            L(f"### {dir_label} — HOD Timing (% of events)")
            L("| Candle Tier | n | At Open | First 30min | First Hour | First 2Hr | Mid-Session | Last Hour |")
            L("|-------------|---|---------|-------------|------------|-----------|-------------|-----------|")
            for _, r in sub.iterrows():
                L(f"| {r['candle_tier']}{r['flag']} | {r['n']} | {r['hod_AT_OPEN']:.1f}% | {r['hod_FIRST_30MIN']:.1f}% | {r['hod_FIRST_HOUR']:.1f}% | {r['hod_FIRST_2HR']:.1f}% | {r['hod_MID_SESSION']:.1f}% | {r['hod_LAST_HOUR']:.1f}% |")
            L()
            L(f"### {dir_label} — LOD Timing (% of events)")
            L("| Candle Tier | n | At Open | First 30min | First Hour | First 2Hr | Mid-Session | Last Hour |")
            L("|-------------|---|---------|-------------|------------|-----------|-------------|-----------|")
            for _, r in sub.iterrows():
                L(f"| {r['candle_tier']}{r['flag']} | {r['n']} | {r['lod_AT_OPEN']:.1f}% | {r['lod_FIRST_30MIN']:.1f}% | {r['lod_FIRST_HOUR']:.1f}% | {r['lod_FIRST_2HR']:.1f}% | {r['lod_MID_SESSION']:.1f}% | {r['lod_LAST_HOUR']:.1f}% |")
            L()

    # ─── TABLE 7 ──────────────────────────────────────────────────
    L("---")
    L()
    L("## Table 7: Ultimate Regime Summary (Indicator Lookup Table)")
    L()
    L("**This is the final cross-tab for ATR_MOOOVVVEE_INDICATOR integration.**")
    L()
    if not t7.empty:
        for direction in ['GAP_DN', 'GAP_UP']:
            sub7 = t7[t7['direction'] == direction]
            if sub7.empty:
                continue
            dir_label = "Gap-Down" if direction == 'GAP_DN' else "Gap-Up"
            L(f"### {dir_label}")
            L("| Gap Bucket | Candle Tier | n | Win Rate | Avg EOD Ret | HOD (ATR) | LOD (ATR) | Med HOD Min | Med LOD Min | FT% | Rev FT% |")
            L("|------------|-------------|---|----------|-------------|-----------|-----------|-------------|-------------|-----|---------|")
            for _, r in sub7.iterrows():
                L(f"| {r['gap_bucket']} | {r['candle_tier']}{r['flag']} | {r['n']} | {r['win_rate']}% | {r['avg_eod_return']:+.3f}% | {r['avg_hod_atr']:.3f} | {r['avg_lod_atr']:.3f} | {r['med_hod_minutes']:.0f} | {r['med_lod_minutes']:.0f} | {r['ft_fire_rate']:.1f}% | {r['rev_ft_fire_rate']:.1f}% |")
            L()

    # ─── KEY FINDINGS SUMMARY ─────────────────────────────────────
    L("---")
    L()
    L("## Key Findings Summary")
    L()

    # Auto-derive insights from the data
    if not t1.empty:
        L("### Gap-Down Bounce — Candle Tier Impact")
        for _, r in t1.iterrows():
            flag = safe_flag(r['n'])
            L(f"- **{r['candle_tier']}** (n={r['n']}{flag}): {r['win_rate']}% WR, avg EOD {r['avg_eod_return']:+.3f}%, "
              f"HOD {r['avg_hod_atr']:.2f}×ATR at ~{r['med_hod_minutes']:.0f}min, "
              f"LOD {r['avg_lod_atr']:.2f}×ATR at ~{r['med_lod_minutes']:.0f}min, "
              f"FT fire {r['ft_fire_rate']:.0f}%")
        L()

    if not t2.empty:
        L("### Gap-Up Fade — Candle Tier Impact")
        for _, r in t2.iterrows():
            flag = safe_flag(r['n'])
            L(f"- **{r['candle_tier']}** (n={r['n']}{flag}): {r['win_rate']}% WR, avg EOD {r['avg_eod_return']:+.3f}%, "
              f"HOD {r['avg_hod_atr']:.2f}×ATR at ~{r['med_hod_minutes']:.0f}min, "
              f"LOD {r['avg_lod_atr']:.2f}×ATR at ~{r['med_lod_minutes']:.0f}min, "
              f"FT fire {r['ft_fire_rate']:.0f}%")
        L()

    # Best regime for max bull/bear
    if not t3.empty:
        max_bull_regimes = t3[t3['candle_tier'] == 'MAX_BULLISH'].sort_values('win_rate', ascending=False)
        if not max_bull_regimes.empty:
            L("### Best Gap-Down Regimes for MAX_BULLISH Opens")
            for _, r in max_bull_regimes.iterrows():
                flag = safe_flag(r['n'])
                L(f"- **{r['gap_bucket']}** (n={r['n']}{flag}): {r['win_rate']}% WR, HOD {r['avg_hod_atr']:.2f}×ATR")
            L()

    if not t4.empty:
        max_bear_regimes = t4[t4['candle_tier'] == 'MAX_BEARISH'].sort_values('win_rate', ascending=False)
        if not max_bear_regimes.empty:
            L("### Best Gap-Up Regimes for MAX_BEARISH Opens")
            for _, r in max_bear_regimes.iterrows():
                flag = safe_flag(r['n'])
                L(f"- **{r['gap_bucket']}** (n={r['n']}{flag}): {r['win_rate']}% WR, LOD {r['avg_lod_atr']:.2f}×ATR")
            L()

    # Reverse FT insights
    if not t5.empty:
        L("### Bearish Bar-1 Reverse FT — The Reversal Pattern")
        for _, r in t5[t5['group'] == 'BEARISH_REVERSED'].iterrows():
            dir_label = "Gap-Down" if r['direction'] == 'GAP_DN' else "Gap-Up"
            flag = safe_flag(r['n'])
            ft_min = f"{r['med_ft_minutes']:.0f}min" if not pd.isna(r['med_ft_minutes']) else "—"
            L(f"- **{dir_label}** (n={r['n']}{flag}): {r['win_rate']}% WR, avg EOD {r['avg_eod_return']:+.3f}%, "
              f"HOD {r['avg_hod_atr']:.2f}×ATR, LOD {r['avg_lod_atr']:.2f}×ATR, "
              f"reverse FT fires at ~{ft_min}")
        L()

    L("---")
    L()
    L("## Implications for ATR_MOOOVVVEE_INDICATOR Rewrite")
    L()
    L("### What This Study Proves/Disproves")
    L("1. **MAX_BULLISH vs BULLISH**: Check Table 1 for whether cs≥70 opens deliver a statistically meaningful edge over regular bullish opens on gap-downs")
    L("2. **Regime-Specific Labels**: Table 7 provides the exact lookup values for win rate, HOD/LOD expectations, and FT fire rates — by direction × gap bucket × candle tier")
    L("3. **Reverse FT Pattern**: Table 5 answers whether bearish bar-1 reversals are tradeable and at what HOD/LOD profile")
    L("4. **Timing Rules**: Table 6 tells the indicator WHEN to expect the session extreme — critical for state engine transitions")
    L()
    L("### Direct Integration Points")
    L("- **Candle tier label**: Replace 3-tier (BULL/NEUTRAL/BEAR) with 5-tier classification on the indicator")
    L("- **Win rate labels**: Use Table 7 values instead of single-number labels — splice by gap bucket + candle tier")
    L("- **HOD/LOD expectations**: Use ATR-normalized values from Table 7 for pullback zone calibration")
    L("- **Reverse FT trigger**: If bearish bar-1 hits reverse FT, upgrade/downgrade the state engine label using Table 5 win rates")
    L("- **Timing bucket rules**: Table 6 values feed the 'when to expect topped/bottomed' state transitions")
    L()
    L("### Sample Size Notes")
    L("- Cells with n < 20 are flagged ⚠️LOW CONFIDENCE")
    L("- Cells with n < 10 are flagged ❌INSUFFICIENT — do not use for indicator rules")
    L("- All unflagged cells have n ≥ 20 and are considered reliable")

    readme_path = STUDY_DIR / "README.md"
    readme_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  Saved: {readme_path}")


# ===============================================================
# MAIN
# ===============================================================

if __name__ == '__main__':
    t_start = time.time()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  OPENING CANDLE STRENGTH × GAP REGIME STUDY                ║")
    print("║  Final ATR_MOOOVVVEE_INDICATOR Data Layer                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Check for cached results
    if EVENT_CACHE.exists():
        print(f"Found intermediate cache: {EVENT_CACHE}")
        print("Skipping API phase — loading from cache")
        df = pd.read_csv(EVENT_CACHE)
        print(f"Loaded {len(df)} events from cache")
    else:
        gap_df = load_gap_events()
        df = process_all_events(gap_df)

    # Run analysis + generate README
    tables = run_analysis(df)
    generate_readme(tables)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"STUDY COMPLETE — {elapsed:.0f}s total")
    print(f"  Events: {len(df)}")
    print(f"  Outputs: {OUTPUTS_DIR}")
    print(f"  README: {STUDY_DIR / 'README.md'}")
    print(f"{'=' * 70}")

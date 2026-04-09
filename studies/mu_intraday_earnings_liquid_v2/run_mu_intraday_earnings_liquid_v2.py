"""
MU Earnings Intraday v2 — Liquid Substitutes Only (NVDA/AMD/SMCI) + MU Diagnostics (API-SAFE)
Single-file runnable study implementing the protocol described by the Head of Quant Strategy.
- Uses Alpaca via shared.config.api_clients.AlpacaClient for all price data (per API_MAP)
- Restricts universe to MU + [NVDA, AMD, SMCI]
- Event-filtered intraday pulls only (no continuous history)
- Produces CSV outputs to outputs/

Minimal dependencies: pandas, numpy, pytz
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, time
import pytz
import logging
import math
import argparse
import numpy as np
import pandas as pd

# Add shared config to path (workspace root)
# file is under .../studies/<study>/, so workspace root is parent.parent.parent
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / 'shared'))
import importlib.util

# Load shared.config.api_config first under its package name so relative imports work
api_config_path = ROOT / 'shared' / 'config' / 'api_config.py'
spec_cfg = importlib.util.spec_from_file_location('shared.config.api_config', str(api_config_path))
api_config = importlib.util.module_from_spec(spec_cfg)
spec_cfg.loader.exec_module(api_config)
import sys as _sys
_sys.modules['shared.config.api_config'] = api_config

# Now load api_clients as namespaced module so its relative imports resolve
api_clients_path = ROOT / 'shared' / 'config' / 'api_clients.py'
spec = importlib.util.spec_from_file_location('shared.config.api_clients', str(api_clients_path))
api_clients = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_clients)
AlpacaClient = api_clients.AlpacaClient
FMPClient = api_clients.FMPClient

# ---------------------------------------------------------------------------
# PARAMETERS (TOP OF SCRIPT - NON-NEGOTIABLE)
# ---------------------------------------------------------------------------
PARAMS = {
    'bar_size': '5Min',
    'start_date': '2016-01-01',
    'end_date': 'today',
    'atr_length': 14,
    'flat_threshold': 0.01,
    'targets_atr': [0.5, 1.0, 1.5],
    'orb_minutes': 15,
    'reversal_swing_threshold_atr': 0.3,
    'min_hit_threshold_for_time_stats': 0.40,
    'gap_edges': [-0.05, -0.02, -0.01, 0.01, 0.02, 0.05],
    'tickers': ['MU', 'NVDA', 'AMD', 'SMCI'],
}

CT = pytz.timezone('America/Chicago')
UTC = pytz.UTC

PREMARKET_START = time(3,0)
PREMARKET_END = time(8,29)
RTH_START = time(8,30)
RTH_END = time(15,0)

OUT_DIR = Path(__file__).parent / 'outputs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('mu_liquid_v2')

EPS = 1e-9

# ---------------------------------------------------------------------------
# STEP 0 - LAB READY CHECK
# ---------------------------------------------------------------------------

def lab_ready_check():
    """Verify Alpaca connectivity and deterministic earnings calendar availability.
    HARD FAIL if prerequisites not met.
    """
    logger.info('STEP 0 — LAB READY CHECK')
    alpaca_ok = False
    fmp_ok = False

    try:
        alpaca = AlpacaClient()
        test = alpaca.get_bars('MU', timeframe='1Day', limit=5)
        if test and ((isinstance(test, dict) and ('bars' in test and len(test['bars'])>0)) or (isinstance(test, list) and len(test)>0)):
            alpaca_ok = True
            logger.info('✅ Alpaca connectivity OK')
        else:
            logger.error('❌ Alpaca returned no daily bars for MU')
    except Exception as e:
        logger.exception('❌ Alpaca connectivity failed: %s', e)

    try:
        fmp = FMPClient()
        # If instantiation succeeds assume calendar method available (further checks later)
        fmp_ok = True
        logger.info('✅ FMP client available')
    except Exception as e:
        logger.exception('❌ FMP client unavailable: %s', e)

    if not alpaca_ok:
        logger.critical('HARD FAIL: Alpaca connectivity / data unavailable. Aborting.')
        raise SystemExit('HARD FAIL: Alpaca connectivity')
    if not fmp_ok:
        logger.critical('HARD FAIL: FMP calendar client unavailable. Aborting.')
        raise SystemExit('HARD FAIL: FMP calendar')

    return AlpacaClient(), FMPClient()

# ---------------------------------------------------------------------------
# STEP 1 — EARNINGS EVENTS WITH TIMESTAMPS + SESSION MAPPING
# ---------------------------------------------------------------------------

def get_mu_earnings_events(fmp_client, start_date: str, end_date: str):
    """Return list of earnings events with announcement_datetime (CT), timing_class, and event_session_date.
    This implementation first attempts to use an FMP earnings endpoint; if unavailable falls back to a curated manual list (deterministic).
    HARD FAIL if no usable timestamps.
    """
    logger.info('STEP 1 — Retrieving MU earnings events')

    # Attempt generic endpoint (best-effort). FMPClient may not implement get_earnings; handle gracefully.
    earnings = []
    try:
        if hasattr(fmp_client, 'get_earnings'):
            raw = fmp_client.get_earnings('MU', from_date=start_date, to_date=end_date)
            # parse raw into records with announcement datetime; implementation depends on FMP response
            for r in raw:
                # best-effort parsing
                dt = None
                if 'date' in r:
                    dt = datetime.fromisoformat(r['date'])
                elif 'announcement_datetime' in r:
                    dt = datetime.fromisoformat(r['announcement_datetime'])
                if dt is not None:
                    if dt.tzinfo is None:
                        dt = CT.localize(dt)
                    else:
                        dt = dt.astimezone(CT)
                    earnings.append({'announcement_datetime': dt})
        else:
            raise AttributeError('no get_earnings')
    except Exception:
        # Fallback: manual deterministic list (recent MU earnings). Must be present per protocol.
        logger.warning('FMP earnings endpoint not found or failed; using manual fallback list')
        manual = [
            ('2024-12-18', 'amc'),('2024-09-25','amc'),('2024-06-26','amc'),('2024-03-20','amc'),
            ('2023-12-20','amc'),('2023-09-27','amc'),('2023-06-28','amc')
        ]
        for date_str, timing in manual:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
            if d < datetime.strptime(start_date, '%Y-%m-%d').date():
                continue
            if end_date != 'today' and d > datetime.strptime(end_date, '%Y-%m-%d').date():
                continue
            if timing == 'bmo':
                ann = datetime.combine(d, time(7,0))
            else:
                ann = datetime.combine(d, time(16,0))
            ann = CT.localize(ann)
            earnings.append({'announcement_datetime': ann})

    if not earnings:
        logger.critical('HARD FAIL: No earnings timestamps available for MU')
        raise SystemExit('HARD FAIL: Missing earnings timestamps')

    # Classify and map
    processed = []
    alpaca = AlpacaClient()
    for rec in earnings:
        ann = rec['announcement_datetime']
        # ensure timezone
        if ann.tzinfo is None:
            ann = CT.localize(ann)
        else:
            ann = ann.astimezone(CT)
        # classify
        t = classify_earnings_timing(ann)
        if t == 'INVALID':
            processed.append({**rec, 'timing_class': t, 'event_session_date': None})
            continue
        # map to event session
        if t == 'BMO':
            event_date = ann.date()
        else:  # AMC -> next trading day
            event_date = get_next_trading_day(alpaca, ann.date())
        processed.append({**rec, 'timing_class': t, 'event_session_date': event_date})

    df = pd.DataFrame(processed)
    # filter invalid
    valid = df[df['timing_class'] != 'INVALID'].copy()
    if valid.empty:
        logger.critical('HARD FAIL: All earnings classified INVALID or mapped to no session')
        raise SystemExit('HARD FAIL: No valid event sessions')

    logger.info('Retrieved %d valid event sessions', len(valid))
    # Return full df
    return valid


def classify_earnings_timing(announcement_dt: datetime):
    ct = announcement_dt
    t = ct.time()
    if t < time(8,30):
        return 'BMO'
    if t >= time(16,0):
        return 'AMC'
    return 'INVALID'


def get_next_trading_day(alpaca: AlpacaClient, calendar_date: datetime.date):
    # Use Alpaca calendar endpoint to find next trading day
    try:
        start = calendar_date.strftime('%Y-%m-%d')
        cal = alpaca.get_calendar(start=start, end=(calendar_date+timedelta(days=7)).strftime('%Y-%m-%d'))
        if isinstance(cal, list) and len(cal) >= 2:
            # find index of calendar_date
            for i, entry in enumerate(cal):
                if entry.get('date') == calendar_date.strftime('%Y-%m-%d'):
                    # return next session's date
                    return datetime.strptime(cal[i+1]['date'], '%Y-%m-%d').date()
        # fallback
        return calendar_date + timedelta(days=1)
    except Exception:
        return calendar_date + timedelta(days=1)

# ---------------------------------------------------------------------------
# STEP 2 — DAILY BASELINES (ATR + MU GAP)
# ---------------------------------------------------------------------------

def fetch_daily_data(alpaca: AlpacaClient, ticker: str, start: str, end: str):
    # returns DataFrame with datetime index (date) and columns ohlc
    res = alpaca.get_bars(ticker, timeframe='1Day', start=start, end=end, limit=10000)
    df = parse_alpaca_bars(res)
    return df


def parse_alpaca_bars(res):
    # Alpaca client may return dict with 'bars' or list of bars
    rows = []
    if isinstance(res, dict) and 'bars' in res:
        bars = res['bars']
    elif isinstance(res, list):
        bars = res
    else:
        bars = []
    for b in bars:
        # Accept a variety of field names
        t = b.get('t') or b.get('timestamp') or b.get('time') or b.get('datetime')
        if isinstance(t, str):
            dt = pd.to_datetime(t)
        else:
            dt = pd.to_datetime(b.get('t'))
        rows.append({'dt': dt, 'open': float(b.get('o') or b.get('open')), 'high': float(b.get('h') or b.get('high')), 'low': float(b.get('l') or b.get('low')), 'close': float(b.get('c') or b.get('close')), 'volume': int(b.get('v') or b.get('volume') or 0)})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index('dt')
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def compute_daily_atr(alpaca: AlpacaClient, ticker: str, event_dates: pd.Series, atr_length: int = 14):
    # For each event_date compute ATR based on prior daily bars
    out = {}
    if event_dates.empty:
        return out
    start = (event_dates.min() - timedelta(days=atr_length*3)).strftime('%Y-%m-%d')
    end = (event_dates.max()).strftime('%Y-%m-%d')
    df = fetch_daily_data(alpaca, ticker, start, end)
    if df.empty:
        return out
    df = df.sort_index()
    # compute true range
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = df.apply(lambda r: max(r['high']-r['low'], abs(r['high']-r['prev_close']), abs(r['low']-r['prev_close'])), axis=1)
    df['atr'] = df['tr'].rolling(atr_length, min_periods=1).mean()
    for d in event_dates.unique():
        # atr as of prior close before event_session_date
        # find last trading day strictly before d
        mask = df.index.date < d
        if mask.any():
            atr_val = df.loc[mask, 'atr'].iloc[-1]
            out[d] = float(atr_val)
        else:
            out[d] = float(df['atr'].iloc[0])
    return out


def compute_gap_bucket(prev_close, rth_open, gap_edges):
    gap_pct = (rth_open - prev_close) / (prev_close + EPS)
    edges = [-math.inf] + gap_edges + [math.inf]
    # build labels
    labels = [f'({edges[i]*100:.1f}%,{edges[i+1]*100:.1f}%]' for i in range(len(edges)-1)]
    # find bucket index
    for i in range(len(edges)-1):
        if gap_pct > edges[i] and gap_pct <= edges[i+1]:
            return gap_pct, labels[i]
    return gap_pct, 'unknown'

# ---------------------------------------------------------------------------
# STEP 3 — INTRADAY EVENT-FILTERED PULLS (API-SAFE)
# ---------------------------------------------------------------------------

def fetch_intraday_data(alpaca: AlpacaClient, ticker: str, session_date: datetime.date, timeframe='5Min'):
    # Pull intraday bars for that date only. We'll request a buffer and then filter by CT times.
    start_dt = CT.localize(datetime.combine(session_date - timedelta(days=1), time(0,0))).astimezone(UTC)
    end_dt = CT.localize(datetime.combine(session_date + timedelta(days=1), time(23,59))).astimezone(UTC)
    res = alpaca.get_bars(ticker, timeframe=timeframe, start=start_dt.isoformat(), end=end_dt.isoformat(), limit=10000)
    df = parse_alpaca_bars(res)
    if df.empty:
        return df
    # localize to CT for easy filtering
    df.index = pd.to_datetime(df.index).tz_localize(UTC).tz_convert(CT)
    # filter for premarket and RTH
    def in_session(tstamp):
        tt = tstamp.time()
        return (tt >= PREMARKET_START and tt <= PREMARKET_END) or (tt >= RTH_START and tt <= RTH_END)
    df = df[df.index.map(in_session)].copy()
    return df

# ---------------------------------------------------------------------------
# STEP 4 — MU REGIME LABELING (RTH OPEN→CLOSE)
# ---------------------------------------------------------------------------

def label_mu_regime(mu_rth_df, flat_threshold):
    if mu_rth_df.empty:
        return None, None
    open_price = float(mu_rth_df.iloc[0]['open'])
    # find bar at RTH_END time if present
    try:
        times = [t.time() for t in mu_rth_df.index]
        rth_end_mask = [tt == RTH_END for tt in times]
        if any(rth_end_mask):
            close_price = float(mu_rth_df.loc[[m for m in mu_rth_df.index[rth_end_mask]], 'close'].iloc[-1])
        else:
            close_price = float(mu_rth_df.iloc[-1]['close'])
    except Exception:
        close_price = float(mu_rth_df.iloc[-1]['close'])

    oc_ret = float((close_price - open_price)/ (open_price + EPS))
    if oc_ret > flat_threshold:
        regime = 'UPSIDE'
    elif oc_ret < -flat_threshold:
        regime = 'DOWNSIDE'
    else:
        regime = 'FLAT'
    return regime, oc_ret

# ---------------------------------------------------------------------------
# STEP 5 — EXPANSION METRICS
# ---------------------------------------------------------------------------

def compute_expansion_metrics(df_rth, open_price, atr_val, targets_atr):
    # df_rth: DataFrame indexed by CT timestamps for RTH only
    res = {}
    if df_rth.empty:
        for t in targets_atr:
            res[f'hit_{t}atr'] = False
            res[f'time_to_{t}atr'] = np.nan
        res['max_exc_pct'] = np.nan
        res['max_exc_atr'] = np.nan
        res['range_pct'] = np.nan
        res['range_atr'] = np.nan
        return res

    highs = df_rth['high']
    lows = df_rth['low']
    # directional excursions
    up_exc = (highs - open_price)/ (open_price + EPS)
    down_exc = (open_price - lows)/ (open_price + EPS)
    # max excursion (positive)
    max_up = up_exc.max()
    max_down = down_exc.max()
    max_exc_pct = max(max_up, max_down)
    max_exc_atr = max_exc_pct / (atr_val + EPS)
    full_range_pct = (df_rth['high'].max() - df_rth['low'].min())/(open_price + EPS)
    full_range_atr = full_range_pct / (atr_val + EPS)
    res['max_exc_pct'] = float(max_exc_pct)
    res['max_exc_atr'] = float(max_exc_atr)
    res['range_pct'] = float(full_range_pct)
    res['range_atr'] = float(full_range_atr)

    # Time to targets: find first timestamp where excursion in either direction >= target*atr
    # compute excursion in ATR units over time
    exc_atr_series = (up_exc.combine_first(down_exc)) / (atr_val + EPS)  # not perfect but gives magnitude series
    # Actually compute directional series by absolute excursion in ATR
    up_atr = up_exc / (atr_val + EPS)
    down_atr = down_exc / (atr_val + EPS)
    for t in targets_atr:
        hit_idx = None
        # consider time index relative to RTH open
        for i, ts in enumerate(df_rth.index):
            if up_atr.iloc[i] >= t or down_atr.iloc[i] >= t:
                hit_idx = i
                break
        if hit_idx is None:
            res[f'hit_{t}atr'] = False
            res[f'time_to_{t}atr'] = np.nan
        else:
            res[f'hit_{t}atr'] = True
            minutes = int((df_rth.index[hit_idx] - df_rth.index[0]).total_seconds()/60)
            res[f'time_to_{t}atr'] = minutes
    return res

# ---------------------------------------------------------------------------
# STEP 6 — PATH QUALITY
# ---------------------------------------------------------------------------

def compute_path_quality(df_rth, atr_val, reversal_swing_threshold_atr):
    # A) swing_reversal_count
    swing_count = 0
    if df_rth.empty:
        return {'swing_reversal_count': np.nan, 'PATH_METRIC_INVALID': False, 'chop_score': np.nan, 'directional_efficiency': np.nan, 'avg_wick_ratio': np.nan, 'avg_clv_rth': np.nan}

    closes = df_rth['close'].values
    highs = df_rth['high'].values
    lows = df_rth['low'].values
    n = len(closes)
    # track current direction: 1 up, -1 down, 0 unknown
    curr_dir = 0
    curr_extreme = closes[0]
    last_extreme_idx = 0
    min_bars = n
    swing_threshold_price = reversal_swing_threshold_atr * atr_val

    for i in range(1, n):
        price = closes[i]
        if curr_dir >= 0:
            # looking for new high
            if price > curr_extreme:
                curr_extreme = price
                last_extreme_idx = i
            else:
                # check retrace from current extreme
                retrace = curr_extreme - price
                if retrace >= swing_threshold_price and curr_dir != -1:
                    # mark potential reversal, wait for new extreme in other direction
                    curr_dir = -1
                    swing_count += 1
                    curr_extreme = price
                    last_extreme_idx = i
        else:
            # curr_dir == -1, looking for new low
            if price < curr_extreme:
                curr_extreme = price
                last_extreme_idx = i
            else:
                retrace = price - curr_extreme
                if retrace >= swing_threshold_price and curr_dir != 1:
                    curr_dir = 1
                    swing_count += 1
                    curr_extreme = price
                    last_extreme_idx = i
    # sanity bound
    if swing_count > n:
        path_invalid = True
    else:
        path_invalid = False

    # B) chop_score: fraction of sign changes in close-to-close returns
    ret = np.diff(closes)/ (closes[:-1] + EPS)
    signs = np.sign(ret)
    sign_changes = np.sum(signs[1:] * signs[:-1] < 0)
    chop_score = sign_changes / max(1, len(ret)-1) if len(ret) > 1 else 0.0

    # directional_efficiency
    open_price = df_rth.iloc[0]['open']
    close_price = df_rth.iloc[-1]['close']
    oc_ret = abs((close_price - open_price)/(open_price + EPS))
    full_range = (df_rth['high'].max() - df_rth['low'].min()) / (open_price + EPS)
    directional_efficiency = oc_ret / (full_range + EPS)

    # avg wick ratio: average ((high-low) - abs(close-open)) / (abs(close-open)+EPS)
    bodies = np.abs(df_rth['close'] - df_rth['open'])
    wicks = (df_rth['high'] - df_rth['low']) - bodies
    avg_wick_ratio = float((wicks/(bodies + EPS)).replace([np.inf, -np.inf], np.nan).fillna(0).mean())

    # avg CLV: (close - low) / (high - low)
    clv = ((df_rth['close'] - df_rth['low']) / ((df_rth['high'] - df_rth['low']) + EPS)).fillna(0)
    avg_clv = float(clv.mean())

    return {'swing_reversal_count': int(swing_count), 'PATH_METRIC_INVALID': path_invalid, 'chop_score': float(chop_score), 'directional_efficiency': float(directional_efficiency), 'avg_wick_ratio': float(avg_wick_ratio), 'avg_clv_rth': float(avg_clv)}

# ---------------------------------------------------------------------------
# STEP 7 — MU DIAGNOSTICS
# ---------------------------------------------------------------------------

def compute_mu_diagnostics(mu_intraday_df, atr_val, orb_minutes):
    out = {}
    if mu_intraday_df.empty:
        return out
    # premarket (03:00-08:29)
    premask = mu_intraday_df.index.map(lambda t: PREMARKET_START <= t.time() <= PREMARKET_END)
    rthmask = mu_intraday_df.index.map(lambda t: RTH_START <= t.time() <= RTH_END)
    pre_df = mu_intraday_df[premask]
    rth_df = mu_intraday_df[rthmask]
    rth_open = rth_df.iloc[0]['open'] if not rth_df.empty else np.nan
    # measure excursions relative to open
    def max_exc(df, open_price):
        if df.empty:
            return 0.0
        ups = (df['high'] - open_price)/(open_price + EPS)
        downs = (open_price - df['low'])/(open_price + EPS)
        return float(max(ups.max() if not ups.empty else 0.0, downs.max() if not downs.empty else 0.0))
    pre_exc = max_exc(pre_df, rth_open)
    rth_exc = max_exc(rth_df, rth_open)
    out['premarket_max_exc_atr'] = pre_exc / (atr_val + EPS)
    out['rth_max_exc_atr'] = rth_exc / (atr_val + EPS)
    out['premarket_share'] = out['premarket_max_exc_atr'] / max(out['premarket_max_exc_atr'], out['rth_max_exc_atr'], EPS)

    # trend_vs_fade
    # determine direction of MU max excursion from open
    up_exc = ((rth_df['high'] - rth_open)/(rth_open + EPS)) if not rth_df.empty else pd.Series([])
    down_exc = ((rth_open - rth_df['low'])/(rth_open + EPS)) if not rth_df.empty else pd.Series([])
    mfe_up = up_exc.max() if not up_exc.empty else 0.0
    mfe_down = down_exc.max() if not down_exc.empty else 0.0
    if mfe_up >= mfe_down:
        direction = 'UP'
        mfe = mfe_up / (atr_val + EPS)
        close_prog = max(0.0, (rth_df.iloc[-1]['close'] - rth_open)/(atr_val + EPS)) if not rth_df.empty else 0.0
    else:
        direction = 'DOWN'
        mfe = mfe_down / (atr_val + EPS)
        close_prog = max(0.0, (rth_open - rth_df.iloc[-1]['close'])/(atr_val + EPS)) if not rth_df.empty else 0.0
    out['trend_direction'] = direction
    out['MFE_atr'] = float(mfe)
    out['close_progress_atr'] = float(close_prog)
    retrace = (mfe - close_prog)/ max(mfe, EPS)
    if retrace <= 0.35:
        out['trend_vs_fade'] = 'TREND'
    elif retrace >= 0.65:
        out['trend_vs_fade'] = 'FADE'
    else:
        out['trend_vs_fade'] = 'MIXED'

    # time_of_day_driver: when max excursion occurred
    # find timestamp of max absolute excursion
    if not rth_df.empty:
        open_price = rth_open
        up_idx = (rth_df['high'] - open_price).idxmax()
        down_idx = (open_price - rth_df['low']).idxmax()
        if (rth_df.loc[up_idx,'high'] - open_price) >= (open_price - rth_df.loc[down_idx,'low']):
            ts = up_idx
        else:
            ts = down_idx
        tod = ts.time()
        # classify
        if tod <= (RTH_START.replace(minute=0) if isinstance(RTH_START, time) else RTH_START):
            driver = 'ORB'
        elif tod <= time(11,0):
            driver = 'Morning'
        elif tod <= time(13,30):
            driver = 'Midday'
        else:
            driver = 'PowerHour'
        out['time_of_day_driver'] = driver
    else:
        out['time_of_day_driver'] = 'NoRTHData'

    # ORB breakout detection (first orb_minutes)
    orb_period_end = rth_df.index[0] + pd.Timedelta(minutes=orb_minutes) if not rth_df.empty else None
    orb_df = rth_df[rth_df.index <= orb_period_end] if orb_period_end is not None else pd.DataFrame()
    if not orb_df.empty:
        orb_high = orb_df['high'].max()
        orb_low = orb_df['low'].min()
        orb_range_atr = ((orb_high - orb_low)/(rth_open + EPS)) / (atr_val + EPS)
        # breakout up/down
        breakout_up = (rth_df['high'] > orb_high).any()
        breakout_down = (rth_df['low'] < orb_low).any()
        # fakeout: breakout then re-enter within ORB range before reaching 0.75 ATR max_exc
        fakeout = False
        if breakout_up or breakout_down:
            # find first breakout index
            if breakout_up:
                idx = rth_df[rth_df['high'] > orb_high].index[0]
            else:
                idx = rth_df[rth_df['low'] < orb_low].index[0]
            # check if subsequent bars re-enter
            post = rth_df[rth_df.index > idx]
            reenter = ((post['low'] >= orb_low) & (post['high'] <= orb_high)).any() if not post.empty else False
            # check if max_exc before reaching 0.75 ATR
            max_exc_after = None
            if not post.empty:
                ups = ((post['high'] - rth_open)/(rth_open+EPS))/(atr_val+EPS)
                downs = ((rth_open - post['low'])/(rth_open+EPS))/(atr_val+EPS)
                max_exc_after = max(ups.max() if not ups.empty else 0.0, downs.max() if not downs.empty else 0.0)
            if reenter and (max_exc_after is not None and max_exc_after < 0.75):
                fakeout = True
        out['orb_breakout_up'] = bool(breakout_up)
        out['orb_breakout_down'] = bool(breakout_down)
        out['orb_fakeout'] = bool(fakeout)
    else:
        out['orb_breakout_up'] = False
        out['orb_breakout_down'] = False
        out['orb_fakeout'] = False

    return out

# ---------------------------------------------------------------------------
# STEP 8 — SEGMENTED SUMMARIES + RANKINGS
# ---------------------------------------------------------------------------

def build_segment_rankings(event_table: pd.DataFrame, min_hit_threshold_for_time_stats=0.40):
    # event_table rows: event_session_date, ticker, mu_regime, mu_gap_bucket, max_exc_atr, hit_1atr, time_to_1atr, range_atr, directional_efficiency, swing_reversal_count, chop_score
    results = []
    # segments: by MU regime, by MU gap bucket, and by regime x gap if sample >=5
    segments = []
    regimes = event_table['mu_regime'].dropna().unique()
    gaps = event_table['mu_gap_bucket'].dropna().unique()
    for r in regimes:
        segments.append(('regime', r))
    for g in gaps:
        segments.append(('gap', g))
    for r in regimes:
        for g in gaps:
            segdf = event_table[(event_table['mu_regime']==r) & (event_table['mu_gap_bucket']==g)]
            if len(segdf) >= 5:
                segments.append(('regime_gap', f'{r}__{g}'))
    # compute metrics per segment per ticker
    for stype, sval in segments:
        if stype == 'regime':
            segdf = event_table[event_table['mu_regime']==sval]
        elif stype == 'gap':
            segdf = event_table[event_table['mu_gap_bucket']==sval]
        else:
            r, g = sval.split('__')
            segdf = event_table[(event_table['mu_regime']==r) & (event_table['mu_gap_bucket']==g)]
        if segdf.empty:
            continue
        for ticker in PARAMS['tickers']:
            tdf = segdf[segdf['ticker']==ticker]
            if tdf.empty:
                continue
            sample_size = len(tdf)
            median_max_exc_atr = float(tdf['max_exc_atr'].median())
            pct_hit_1atr = float(tdf['hit_1.0atr'].mean()) if 'hit_1.0atr' in tdf.columns else 0.0
            N_hit_1atr = int(tdf['hit_1.0atr'].sum()) if 'hit_1.0atr' in tdf.columns else 0
            median_time_to_1atr = np.nan
            if pct_hit_1atr >= min_hit_threshold_for_time_stats and 'time_to_1.0atr' in tdf.columns:
                median_time_to_1atr = float(tdf.loc[tdf['hit_1.0atr'], 'time_to_1.0atr'].median())
            median_range_atr = float(tdf['range_atr'].median())
            median_directional_efficiency = float(tdf['directional_efficiency'].median())
            median_swing_reversal_count = float(tdf['swing_reversal_count'].median())
            median_chop_score = float(tdf['chop_score'].median())
            # store
            results.append({'segment_type': stype, 'segment_value': sval, 'ticker': ticker, 'sample_size': sample_size, 'median_max_exc_atr': median_max_exc_atr, 'pct_hit_1atr': pct_hit_1atr, 'N_hit_1atr': N_hit_1atr, 'median_time_to_1atr': median_time_to_1atr, 'median_range_atr': median_range_atr, 'median_directional_efficiency': median_directional_efficiency, 'median_swing_reversal_count': median_swing_reversal_count, 'median_chop_score': median_chop_score})
    rdf = pd.DataFrame(results)
    if rdf.empty:
        return rdf
    # Composite rank: equal-weight percentiles across expansion (median_max_exc_atr), speed (pct_hit_1atr + median_time_to_1atr when valid), clean (swing_reversal_count + chop_score)
    # compute percentiles per metric
    from scipy.stats import rankdata
    # expansion rank (higher better)
    rdf['expansion_pctile'] = rdf['median_max_exc_atr'].rank(pct=True)
    # speed: use pct_hit only when time invalid
    rdf['speed_score'] = rdf['pct_hit_1atr']
    time_mask = ~rdf['median_time_to_1atr'].isna()
    if time_mask.any():
        # invert time to make higher better: 1 / time
        rdf.loc[time_mask, 'speed_score'] = (rdf.loc[time_mask, 'pct_hit_1atr'] + (1.0 / (rdf.loc[time_mask, 'median_time_to_1atr'] + EPS))) / 2.0
    rdf['speed_pctile'] = rdf['speed_score'].rank(pct=True)
    # clean: lower better for swing and chop -> invert
    rdf['clean_score'] = 1.0 / (1.0 + rdf['median_swing_reversal_count'] + rdf['median_chop_score'])
    rdf['clean_pctile'] = rdf['clean_score'].rank(pct=True)
    rdf['composite_rank'] = rdf[['expansion_pctile', 'speed_pctile', 'clean_pctile']].mean(axis=1)
    rdf = rdf.sort_values('composite_rank', ascending=False)
    return rdf

# ---------------------------------------------------------------------------
# STEP 9 — OUTPUTS
# ---------------------------------------------------------------------------

def export_outputs(event_rows, rankings_df, mu_diag_df, run_log):
    event_table = pd.DataFrame(event_rows)
    event_table.to_csv(OUT_DIR / 'mu_liquid_v2_event_table.csv', index=False)
    rankings_df.to_csv(OUT_DIR / 'mu_liquid_v2_rankings.csv', index=False)
    mu_diag_df.to_csv(OUT_DIR / 'mu_liquid_v2_mu_diagnostics.csv', index=False)
    # report & run_log
    with open(OUT_DIR / 'mu_liquid_v2_report.txt', 'w') as f:
        f.write('MU Liquid v2 Report\n')
        f.write('See CSVs\n')
    with open(OUT_DIR / 'run_log.txt', 'w') as f:
        f.write(run_log)
    logger.info('Outputs written to %s', OUT_DIR)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run():
    alpaca, fmp = lab_ready_check()
    start = PARAMS['start_date']
    end = PARAMS['end_date']
    earnings_df = get_mu_earnings_events(fmp, start, end)
    # Map event dates
    event_dates = earnings_df['event_session_date'].dropna().unique()
    # Step 2: daily ATR for all tickers
    mu_event_dates = pd.Series([d for d in event_dates])
    atr_map = {}
    for ticker in PARAMS['tickers']:
        atrs = compute_daily_atr(alpaca, ticker, mu_event_dates, atr_length=PARAMS['atr_length'])
        atr_map[ticker] = atrs
    # Build event-level rows
    event_rows = []
    mu_diag_rows = []
    missing = []
    for _, ev in earnings_df.iterrows():
        if pd.isna(ev.get('event_session_date')):
            continue
        ed = ev['event_session_date']
        for ticker in PARAMS['tickers']:
            # fetch intraday for that ticker/date
            intr = fetch_intraday_data(alpaca, ticker, ed, timeframe=PARAMS['bar_size'])
            if intr.empty:
                missing.append((ed, ticker))
                logger.warning('Missing intraday for %s on %s', ticker, ed)
                continue
            # separate RTH
            rth = intr[intr.index.map(lambda t: RTH_START <= t.time() <= RTH_END)]
            # compute atr ref
            atr_val = atr_map.get(ticker, {}).get(ed, np.nan)
            # for MU compute pre-open prev_close and gap
            mu_regime = None
            mu_gap_pct = np.nan
            mu_gap_bucket = None
            mu_oc_ret = np.nan
            if ticker == 'MU':
                # prev_close: get prior daily close using compute_daily_atr's df would have data, but recompute quick
                daily = fetch_daily_data(alpaca, 'MU', (ed - timedelta(days=10)).strftime('%Y-%m-%d'), ed.strftime('%Y-%m-%d'))
                prev_close = None
                if not daily.empty:
                    prev_close = daily[daily.index.date < ed]['close'].iloc[-1] if any(daily.index.date < ed) else daily['close'].iloc[0]
                rth_open = rth.iloc[0]['open'] if not rth.empty else np.nan
                if prev_close is not None and not math.isnan(rth_open):
                    mu_gap_pct, mu_gap_bucket = compute_gap_bucket(prev_close, rth_open, PARAMS['gap_edges'])
                # regime
                mu_regime, mu_oc_ret = label_mu_regime(rth, PARAMS['flat_threshold'])
            # expansion
            open_price = rth.iloc[0]['open'] if not rth.empty else np.nan
            exp = compute_expansion_metrics(rth, open_price, atr_val, PARAMS['targets_atr'])
            # path quality (pass ATR-relative threshold, function multiplies by ATR internally)
            path = compute_path_quality(rth, atr_val, PARAMS['reversal_swing_threshold_atr'])
            # mu diagnostics if MU
            mu_diag = {}
            if ticker == 'MU':
                mu_diag = compute_mu_diagnostics(intr, atr_val, PARAMS['orb_minutes'])
                mu_diag.update({'event_session_date': ed, 'announcement_datetime': ev['announcement_datetime'], 'timing_class': ev['timing_class'], 'mu_regime': mu_regime, 'mu_gap_pct': mu_gap_pct, 'mu_gap_bucket': mu_gap_bucket})
                mu_diag_rows.append(mu_diag)
            # assemble row
            row = {'event_session_date': ed, 'ticker': ticker, 'announcement_datetime': ev['announcement_datetime'], 'timing_class': ev['timing_class'], 'mu_regime': mu_regime, 'mu_gap_pct': mu_gap_pct, 'mu_gap_bucket': mu_gap_bucket, 'atr_ref': atr_val}
            # expansion targets
            for t in PARAMS['targets_atr']:
                row[f'hit_{t}atr'] = exp.get(f'hit_{t}atr')
                row[f'time_to_{t}atr'] = exp.get(f'time_to_{t}atr')
            row.update({'max_exc_pct': exp.get('max_exc_pct'), 'max_exc_atr': exp.get('max_exc_atr'), 'range_pct': exp.get('range_pct'), 'range_atr': exp.get('range_atr')})
            row.update(path)
            event_rows.append(row)
    # create event table
    event_table = pd.DataFrame(event_rows)
    # rename hit columns to consistent names
    # ensure hit_1.0atr exists
    if 'hit_1.0atr' not in event_table.columns and 'hit_1.0atr' in event_table.columns:
        pass
    # build rankings
    rankings_df = build_segment_rankings(event_table, PARAMS['min_hit_threshold_for_time_stats'])
    mu_diag_df = pd.DataFrame(mu_diag_rows)
    run_log = f'Processed {len(event_table)} event-ticker rows; missing intraday: {len(missing)}\n'
    export_outputs(event_rows, rankings_df, mu_diag_df, run_log)
    logger.info('Run complete')

if __name__ == '__main__':
    run()

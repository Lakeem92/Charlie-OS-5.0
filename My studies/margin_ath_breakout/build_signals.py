"""
╔══════════════════════════════════════════════════════════════════════╗
║  MARGIN ATH BREAKOUT — Phase 2: Signal Construction                ║
║                                                                    ║
║  For each (ticker, quarter) where ≥1 margin hit a 3yr+ high:      ║
║    → Anchor on accepted_date (SEC filing visible to the market)    ║
║    → Scan the next 60 trading days for the first ATH breakout      ║
║    → If found: signal fires, classified by margin combo            ║
║                                                                    ║
║  Also builds 3 control groups:                                     ║
║    Control A — Pure ATH breakouts (no margin milestone nearby)     ║
║    Control B — Margin milestone present but no ATH follow-through  ║
║    Control C — Random trading days (n matched to signal count)     ║
║                                                                    ║
║  Output: data/signals_final.parquet                                ║
║  Usage:  python build_signals.py                                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import random
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════
# PATHS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════

STUDY_DIR    = Path(r'C:\QuantLab\Data_Lab\studies\margin_ath_breakout')
DATA_DIR     = STUDY_DIR / 'data'
PRICES_DIR   = DATA_DIR / 'prices'
FUND_PATH    = DATA_DIR / 'fundamentals_signals.parquet'
SIGNALS_PATH = DATA_DIR / 'signals_final.parquet'

ATH_WINDOW_DAYS   = 60   # trading days post-earnings to find first ATH breakout
DEDUP_WINDOW_DAYS = 60   # trading days lockout between signals for same ticker
CTRL_A_LOOKBACK   = 90   # calendar days — Control A: no margin signal within this window
CTRL_A_MAX_MULT   = 3    # cap Control A size at 3× signal count
RANDOM_SEED       = 42

# Margin combination labels (3-tuple: gross, operating, ebitda)
COMBO_LABELS = {
    (True,  False, False): 'GROSS_ONLY',
    (False, True,  False): 'OPERATING_ONLY',
    (False, False, True):  'EBITDA_ONLY',
    (True,  True,  False): 'GROSS+OPERATING',
    (True,  False, True):  'GROSS+EBITDA',
    (False, True,  True):  'OPERATING+EBITDA',
    (True,  True,  True):  'ALL_THREE',
}

# ── PRINT HEADER ────────────────────────────────────────────────────

print('=' * 70)
print('MARGIN ATH BREAKOUT — SIGNAL CONSTRUCTION')
print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('=' * 70)

# ══════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════

if not FUND_PATH.exists():
    print(f'ERROR: {FUND_PATH} not found. Run collect_data.py first.')
    sys.exit(1)

fundamentals = pd.read_parquet(FUND_PATH)
fundamentals['date']          = pd.to_datetime(fundamentals['date'])
fundamentals['accepted_date'] = pd.to_datetime(fundamentals['accepted_date']).dt.normalize()

signal_candidates = fundamentals[fundamentals['has_any_3yr_signal']].copy()

print(f'\nLoaded fundamentals:  {len(fundamentals)} records | '
      f'{fundamentals["ticker"].nunique()} tickers')
print(f'Signal candidates:    {len(signal_candidates)} quarter-events with ≥1 margin at 3yr high\n')

# ══════════════════════════════════════════════════════════════════════
# PRICE CACHE — load all parquets into memory once
# ══════════════════════════════════════════════════════════════════════

print('Loading price data into memory...')
price_dict = {}
missing_price = []

for ticker in fundamentals['ticker'].unique():
    path = PRICES_DIR / f'{ticker}.parquet'
    if path.exists():
        df = pd.read_parquet(path)
        idx = pd.to_datetime(df.index)
        if idx.tz is not None:
            idx = idx.tz_convert('UTC').tz_localize(None)
        df.index = idx.normalize()
        df = df.sort_index()
        price_dict[ticker] = df
    else:
        missing_price.append(ticker)

print(f'  Loaded: {len(price_dict)} tickers | '
      f'Missing price files: {len(missing_price)}')
if missing_price:
    print(f'  No price data: {", ".join(missing_price[:10])}'
          + (f' ... +{len(missing_price)-10} more' if len(missing_price) > 10 else ''))

# ══════════════════════════════════════════════════════════════════════
# PHASE 1: BUILD SIGNAL EVENTS
# ══════════════════════════════════════════════════════════════════════

print('\n' + '-' * 60)
print('PHASE 1: Finding first ATH breakout within 60 trading days of earnings...')

signal_rows   = []
no_ath_count  = 0
no_price_count = 0

for _, row in signal_candidates.iterrows():
    ticker       = row['ticker']
    accepted_dt  = row['accepted_date']

    if ticker not in price_dict:
        no_price_count += 1
        continue

    pf = price_dict[ticker]

    # All trading days on or after accepted_date
    future_idx = pf.index[pf.index >= accepted_dt]
    if len(future_idx) == 0:
        no_ath_count += 1
        continue

    # Limit to the ATH detection window
    window_idx  = future_idx[:ATH_WINDOW_DAYS]
    ath_in_win  = pf.loc[window_idx, 'is_ath']
    ath_days    = ath_in_win[ath_in_win == True].index

    if len(ath_days) == 0:
        no_ath_count += 1
        continue

    signal_date  = ath_days[0]
    days_to_ath  = int(((pf.index >= accepted_dt) & (pf.index <= signal_date)).sum()) \
                   if len(window_idx) > 0 else 0

    g  = bool(row.get('gross_3yr_high',     False))
    op = bool(row.get('operating_3yr_high', False))
    eb = bool(row.get('ebitda_3yr_high',    False))

    signal_rows.append({
        'ticker':              ticker,
        'quarter_end':         row['date'],
        'accepted_date':       accepted_dt,
        'signal_date':         signal_date,
        'days_to_ath':         days_to_ath,
        'is_gross_3yr':        g,
        'is_operating_3yr':    op,
        'is_ebitda_3yr':       eb,
        'is_gross_5yr':        bool(row.get('gross_5yr_high',     False)),
        'is_operating_5yr':    bool(row.get('operating_5yr_high', False)),
        'is_ebitda_5yr':       bool(row.get('ebitda_5yr_high',    False)),
        'is_gross_10yr':       bool(row.get('gross_10yr_high',     False)),
        'is_operating_10yr':   bool(row.get('operating_10yr_high', False)),
        'is_ebitda_10yr':      bool(row.get('ebitda_10yr_high',    False)),
        'n_margins_3yr':       int(row.get('n_3yr_signals', 0)),
        'gross_margin':        float(row.get('gross_margin',     np.nan)),
        'operating_margin':    float(row.get('operating_margin', np.nan)),
        'ebitda_margin':       float(row.get('ebitda_margin',    np.nan)),
        'group':               'SIGNAL',
    })

signals_df = pd.DataFrame(signal_rows)
print(f'  Raw signals found:         {len(signals_df)}')
print(f'  No ATH in window:          {no_ath_count}')
print(f'  No price data:             {no_price_count}')

# ── Assign margin combo label ────────────────────────────────────────
if len(signals_df) > 0:
    signals_df['margin_combo'] = signals_df.apply(
        lambda r: COMBO_LABELS.get(
            (r['is_gross_3yr'], r['is_operating_3yr'], r['is_ebitda_3yr']), 'UNKNOWN'),
        axis=1
    )
    signals_df['stacking_tier'] = signals_df['n_margins_3yr'].map(
        {0: 'NONE', 1: 'SINGLE', 2: 'DOUBLE', 3: 'TRIPLE'})
else:
    print('\nWARNING: No signal events found. Check that collect_data.py ran successfully.')
    sys.exit(1)

# ── Deduplication: 60-trading-day lockout per ticker ────────────────
print('\n' + '-' * 60)
print('PHASE 2: Deduplicating signals (60-trading-day lockout per ticker)...')

signals_df = signals_df.sort_values('signal_date').reset_index(drop=True)
keep        = []
last_sig    = {}   # ticker → last kept signal_date

for _, row in signals_df.iterrows():
    ticker = row['ticker']
    sd     = pd.Timestamp(row['signal_date'])

    if ticker not in last_sig:
        keep.append(True)
        last_sig[ticker] = sd
        continue

    prior = last_sig[ticker]
    pf    = price_dict.get(ticker)
    if pf is not None:
        td_between = int(((pf.index >= prior) & (pf.index <= sd)).sum())
    else:
        td_between = int((sd - prior).days * 5 / 7)  # approx

    if td_between >= DEDUP_WINDOW_DAYS:
        keep.append(True)
        last_sig[ticker] = sd
    else:
        keep.append(False)

signals_df = signals_df[keep].reset_index(drop=True)
print(f'  After dedup: {len(signals_df)} clean signal events')

# ══════════════════════════════════════════════════════════════════════
# PHASE 3: CONTROL GROUPS
# ══════════════════════════════════════════════════════════════════════

print('\n' + '-' * 60)
print('PHASE 3: Building control groups...')

fund_tickers = list(price_dict.keys())

# ── CONTROL B: Margin signal present but no ATH within 60 trading days ──
# (margin milestone without price confirmation)
print('  [B] Margin high with no ATH follow-through...')

signal_keys = set(zip(signals_df['ticker'], signals_df['quarter_end']))

ctrl_b_rows = []
for _, row in signal_candidates.iterrows():
    key = (row['ticker'], row['date'])
    if key not in signal_keys:
        g  = bool(row.get('gross_3yr_high',     False))
        op = bool(row.get('operating_3yr_high', False))
        eb = bool(row.get('ebitda_3yr_high',    False))
        ctrl_b_rows.append({
            'ticker':        row['ticker'],
            'signal_date':   row['accepted_date'],
            'group':         'CONTROL_B',
            'margin_combo':  COMBO_LABELS.get((g, op, eb), 'UNKNOWN'),
            'n_margins_3yr': int(row.get('n_3yr_signals', 0)),
        })

ctrl_b_df = pd.DataFrame(ctrl_b_rows)
print(f'    Control B: {len(ctrl_b_df)} events')

# ── CONTROL A: Pure ATH breakouts — no margin signal in prior 90 calendar days ──
# Uses merge_asof per ticker for efficiency
print('  [A] Pure ATH breakouts (no margin signal in prior 90 days)...')

# Build margin signal dates for all tickers
sig_dates_all = fundamentals[fundamentals['has_any_3yr_signal']][
    ['ticker', 'accepted_date']].copy()
sig_dates_all['accepted_date'] = pd.to_datetime(sig_dates_all['accepted_date']).dt.normalize()

ctrl_a_rows = []

for ticker, pf in price_dict.items():
    # All ATH breakout dates for this ticker
    ath_idx = pf.index[pf['is_ath'] == True]
    if len(ath_idx) == 0:
        continue

    ath_series = pd.DataFrame({'ath_date': ath_idx}).sort_values('ath_date')

    # Margin signals for this ticker
    sig_series = sig_dates_all[sig_dates_all['ticker'] == ticker][
        ['accepted_date']].sort_values('accepted_date').rename(
        columns={'accepted_date': 'last_sig_date'})

    if len(sig_series) == 0:
        # No margin signals at all → every ATH day is pure ATH
        for d in ath_idx:
            ctrl_a_rows.append({'ticker': ticker, 'ath_date': d, 'no_recent_sig': True})
        continue

    # merge_asof: for each ATH date, find the closest margin signal on or before it
    merged = pd.merge_asof(
        ath_series,
        sig_series,
        left_on='ath_date',
        right_on='last_sig_date',
        direction='backward',
    )

    # Keep rows where no margin signal exists in the prior CTRL_A_LOOKBACK calendar days
    merged['days_since_sig'] = (merged['ath_date'] - merged['last_sig_date']).dt.days
    no_recent = merged['last_sig_date'].isna() | (merged['days_since_sig'] > CTRL_A_LOOKBACK)

    for _, r in merged[no_recent].iterrows():
        ctrl_a_rows.append({'ticker': r['ticker'] if 'ticker' in r else ticker,
                             'ath_date': r['ath_date'],
                             'no_recent_sig': True})

# Add missing ticker column if absent
ctrl_a_all = pd.DataFrame(ctrl_a_rows)
if 'ticker' not in ctrl_a_all.columns:
    # ticker was not added in the no-sig-series path; rebuild
    ctrl_a_all = ctrl_a_all.copy()

print(f'    Control A (full):  {len(ctrl_a_all)} pure ATH breakout days')

# Random-sample Control A to at most 3× signal count
random.seed(RANDOM_SEED)
cap = len(signals_df) * CTRL_A_MAX_MULT
if len(ctrl_a_all) > cap:
    ctrl_a_all = ctrl_a_all.sample(n=cap, random_state=RANDOM_SEED).reset_index(drop=True)

ctrl_a_df = pd.DataFrame({
    'ticker':        ctrl_a_all['ticker'] if 'ticker' in ctrl_a_all.columns else '',
    'signal_date':   pd.to_datetime(ctrl_a_all['ath_date']),
    'group':         'CONTROL_A',
    'margin_combo':  'NONE',
    'n_margins_3yr': 0,
})
print(f'    Control A (sampled to {CTRL_A_MAX_MULT}×): {len(ctrl_a_df)} events')

# ── CONTROL C: Random trading days, n matched to signal count ──────
print('  [C] Random trading days (n matched to signal count)...')

all_td = []
for ticker, pf in price_dict.items():
    for d in pf.index:
        all_td.append((ticker, d))

random.seed(RANDOM_SEED)
n_random = len(signals_df)
sampled_td = random.sample(all_td, min(n_random, len(all_td)))

ctrl_c_df = pd.DataFrame({
    'ticker':        [t for t, _ in sampled_td],
    'signal_date':   pd.to_datetime([d for _, d in sampled_td]),
    'group':         'CONTROL_C',
    'margin_combo':  'NONE',
    'n_margins_3yr': 0,
})
print(f'    Control C: {len(ctrl_c_df)} random trading days')

# ══════════════════════════════════════════════════════════════════════
# COMBINE AND SAVE
# ══════════════════════════════════════════════════════════════════════

# Ensure consistent columns before concat
filler_cols = [
    'quarter_end', 'accepted_date', 'days_to_ath',
    'is_gross_3yr', 'is_operating_3yr', 'is_ebitda_3yr',
    'is_gross_5yr', 'is_operating_5yr', 'is_ebitda_5yr',
    'is_gross_10yr', 'is_operating_10yr', 'is_ebitda_10yr',
    'gross_margin', 'operating_margin', 'ebitda_margin',
    'stacking_tier',
]
for part in [ctrl_a_df, ctrl_b_df, ctrl_c_df]:
    for col in filler_cols:
        if col not in part.columns:
            part[col] = np.nan

all_events = pd.concat(
    [signals_df, ctrl_a_df, ctrl_b_df, ctrl_c_df],
    ignore_index=True,
    sort=False,
)
all_events['signal_date'] = pd.to_datetime(all_events['signal_date'])
all_events = all_events.sort_values('signal_date').reset_index(drop=True)
all_events.to_parquet(SIGNALS_PATH)

# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════

print('\n' + '=' * 70)
print('SIGNAL CONSTRUCTION SUMMARY')
print('=' * 70)
print(f'  SIGNAL events (≥1 margin 3yr high + ATH breakout):  {len(signals_df):>5}')
print(f'  CONTROL A  (pure ATH, no nearby margin catalyst):   {len(ctrl_a_df):>5}')
print(f'  CONTROL B  (margin high, no ATH follow-through):    {len(ctrl_b_df):>5}')
print(f'  CONTROL C  (random trading days):                   {len(ctrl_c_df):>5}')
print(f'  TOTAL rows saved:                                   {len(all_events):>5}')

print('\nSignal breakdown by margin combination:')
if len(signals_df) > 0:
    combo_counts = signals_df['margin_combo'].value_counts()
    for combo, cnt in combo_counts.items():
        bar = '█' * min(cnt, 40)
        print(f'  {combo:<20} {cnt:>4}  {bar}')

print('\nSignal breakdown by stacking tier:')
if len(signals_df) > 0:
    for tier, cnt in signals_df['stacking_tier'].value_counts().items():
        print(f'  {tier:<10} {cnt:>4}')

print(f'\nSaved: {SIGNALS_PATH}')
print(f'Next:  python analyze.py')
print('=' * 70)

"""
MARGIN ATH BREAKOUT -- Phase 1: Data Collection

Fundamentals: SEC EDGAR XBRL API (free, no key, 10+ years quarterly)
  - GrossProfit, RevenueFromContractWithCustomer, OperatingIncomeLoss
  - Uses 'filed' date as announcement anchor (exact SEC public timestamp)
  - Filters to single-quarter rows via period duration (<100 days)

Prices: Alpaca daily OHLCV via DataRouter (2010+)
  - Rolling ATH flag: no look-ahead bias

Usage:
  python collect_data.py               (uses cache)
  python collect_data.py --force       (re-pulls everything)
  python collect_data.py --force-fund  (re-pulls EDGAR only)
  python collect_data.py --force-prices (re-pulls Alpaca only)
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import time
import argparse
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path

from shared.watchlist import get_watchlist
from shared.data_router import DataRouter

# ── PATHS ──────────────────────────────────────────────────────────────
STUDY_DIR  = Path(r'C:\QuantLab\Data_Lab\studies\margin_ath_breakout')
DATA_DIR   = STUDY_DIR / 'data'
PRICES_DIR = DATA_DIR / 'prices'
FUND_PATH  = DATA_DIR / 'fundamentals_signals.parquet'
CIK_CACHE  = DATA_DIR / 'cik_map.parquet'

PRICE_START    = '2010-01-01'
PRICE_END      = datetime.now().strftime('%Y-%m-%d')
EDGAR_DELAY    = 0.12   # ~8 req/sec (SEC recommends <=10/sec)
MILESTONE_3YR  = 12
MILESTONE_5YR  = 20
MILESTONE_10YR = 40
SINGLE_QTR_MAX_DAYS = 100  # filter YTD rows; single quarter <= ~98 days

EDGAR_HEADERS = {
    'User-Agent': 'QuantLab research@quantlab.local',
    'Accept-Encoding': 'gzip, deflate',
}

# EDGAR XBRL tag candidates in priority order
REV_TAGS = [
    'RevenueFromContractWithCustomerExcludingAssessedTax',
    'RevenueFromContractWithCustomerIncludingAssessedTax',
    'Revenues',
    'SalesRevenueNet',
    'SalesRevenueGoodsNet',
    'RevenueFromContractWithCustomer',
]
GP_TAGS  = ['GrossProfit']
OI_TAGS  = ['OperatingIncomeLoss', 'OperatingIncome']

KNOWN_ETFS = {
    'SPY','QQQ','IWM','DIA','GLD','SLV','TLT','HYG','LQD',
    'XLF','XLK','XLE','XLV','XLI','XLU','XLP','XLY','XLB',
    'XLRE','XLC','EEM','EFA','VXX','UVXY','SQQQ','TQQQ',
    'SPXU','SPXL','SOXL','SOXS','ARKK','ARKG','ARKW','ARKQ',
    'SMH','SOXX','IBB','XBI','KRE','GDX','GDXJ',
    'USO','UNG','AMLP','JETS','CQQQ','KWEB','FXI','AIQ',
}

for d in [DATA_DIR, PRICES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── ARGS ───────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument('--force',         action='store_true')
ap.add_argument('--force-fund',    action='store_true')
ap.add_argument('--force-prices',  action='store_true')
args, _ = ap.parse_known_args()
force_fund   = args.force or args.force_fund
force_prices = args.force or args.force_prices

# ── HELPERS ────────────────────────────────────────────────────────────
def flag_rolling_highs(s, label):
    """Flag each row as a new N-year high using only prior data (no look-ahead)."""
    prior_max = s.shift(1).expanding().max()
    n_prior   = s.shift(1).expanding().count().fillna(0)
    is_high   = s > prior_max
    return pd.DataFrame({
        label + '_3yr_high':  is_high & (n_prior >= MILESTONE_3YR)  & s.notna(),
        label + '_5yr_high':  is_high & (n_prior >= MILESTONE_5YR)  & s.notna(),
        label + '_10yr_high': is_high & (n_prior >= MILESTONE_10YR) & s.notna(),
    })


def extract_quarter_series(facts, tags):
    """
    Try each XBRL tag in order; return DataFrame of single-quarter USD rows.
    Columns: end (Timestamp), val (float), filed (Timestamp)
    Single-quarter = period <= SINGLE_QTR_MAX_DAYS days.
    Deduplicates on end date, keeping the earliest-filed row.
    """
    usgaap = facts.get('facts', {}).get('us-gaap', {})
    for tag in tags:
        if tag not in usgaap:
            continue
        rows = usgaap[tag].get('units', {}).get('USD', [])
        records = []
        for r in rows:
            if r.get('form') not in ('10-Q', '10-K'):
                continue
            start = r.get('start')
            end   = r.get('end')
            if not start or not end:
                continue
            try:
                dt_s = pd.Timestamp(start)
                dt_e = pd.Timestamp(end)
                if (dt_e - dt_s).days > SINGLE_QTR_MAX_DAYS:
                    continue
            except Exception:
                continue
            filed = r.get('filed')
            records.append({
                'end':   dt_e,
                'val':   float(r['val']),
                'filed': pd.Timestamp(filed) if filed else dt_e + pd.Timedelta(days=45),
            })
        if not records:
            continue
        df = (pd.DataFrame(records)
              .sort_values('filed')
              .drop_duplicates(subset='end', keep='first')
              .sort_values('end')
              .reset_index(drop=True))
        return df
    return pd.DataFrame(columns=['end', 'val', 'filed'])


def pull_edgar(ticker, cik):
    """Pull quarterly fundamentals from SEC EDGAR XBRL for one ticker."""
    url = 'https://data.sec.gov/api/xbrl/companyfacts/CIK' + cik + '.json'
    try:
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=25)
        if resp.status_code != 200:
            return None
        facts = resp.json()
    except Exception:
        return None

    rev_df = extract_quarter_series(facts, REV_TAGS)
    gp_df  = extract_quarter_series(facts, GP_TAGS)
    oi_df  = extract_quarter_series(facts, OI_TAGS)

    if len(rev_df) < 5 or rev_df['val'].abs().max() == 0:
        return None

    # Build merged frame
    df = rev_df.rename(columns={'val': 'revenue', 'filed': 'accepted_date'})
    if len(gp_df):
        df = df.merge(gp_df[['end', 'val']].rename(columns={'val': 'gross_profit'}),
                      on='end', how='left')
    else:
        df['gross_profit'] = np.nan
    if len(oi_df):
        df = df.merge(oi_df[['end', 'val']].rename(columns={'val': 'op_income'}),
                      on='end', how='left')
    else:
        df['op_income'] = np.nan

    rev = df['revenue'].replace(0, np.nan)
    df['gross_margin']     = df['gross_profit'] / rev
    df['operating_margin'] = df['op_income']    / rev
    df['ebitda_margin']    = np.nan  # EDGAR lacks clean single EBITDA tag

    df = df[df['revenue'] > 0].copy()
    if len(df) < 5:
        return None

    df['ticker'] = ticker
    df = df.rename(columns={'end': 'date'})
    df = df.sort_values('date').reset_index(drop=True)

    # Rolling high flags (sorted oldest-first required)
    for col, lbl in [('gross_margin', 'gross'), ('operating_margin', 'operating')]:
        df = pd.concat([df, flag_rolling_highs(df[col], lbl)], axis=1)
    for sfx in ['3yr', '5yr', '10yr']:
        df['ebitda_' + sfx + '_high'] = False

    df['n_3yr_signals']      = (df['gross_3yr_high'].astype(int) +
                                 df['operating_3yr_high'].astype(int))
    df['has_any_3yr_signal'] = df['n_3yr_signals'] > 0

    keep = ['ticker', 'date', 'accepted_date',
            'gross_margin', 'operating_margin', 'ebitda_margin',
            'gross_3yr_high', 'operating_3yr_high', 'ebitda_3yr_high',
            'gross_5yr_high', 'operating_5yr_high', 'ebitda_5yr_high',
            'gross_10yr_high', 'operating_10yr_high', 'ebitda_10yr_high',
            'n_3yr_signals', 'has_any_3yr_signal']
    return df[[c for c in keep if c in df.columns]]


# ══════════════════════════════════════════════════════════════════════
print('=' * 70)
print('MARGIN ATH BREAKOUT -- DATA COLLECTION (SEC EDGAR XBRL)')
print('Date: ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print('=' * 70)

raw     = get_watchlist()
tickers = [t for t in raw if t.upper() not in KNOWN_ETFS]
print('\nUniverse: ' + str(len(tickers)) + ' tickers (' +
      str(len(raw) - len(tickers)) + ' ETFs removed)\n')

# ══════════════════════════════════════════════════════════════════════
# PHASE 1A: TICKER -> CIK MAP
# ══════════════════════════════════════════════════════════════════════
if not force_fund and CIK_CACHE.exists():
    cik_df  = pd.read_parquet(CIK_CACHE)
    cik_map = dict(zip(cik_df['ticker'], cik_df['cik']))
    print('[CACHE] CIK map: ' + str(len(cik_map)) + ' entries')
else:
    print('Fetching SEC company tickers map...')
    cik_resp = requests.get('https://www.sec.gov/files/company_tickers.json',
                            headers=EDGAR_HEADERS, timeout=20)
    raw_map  = cik_resp.json()
    cik_map  = {v['ticker']: str(v['cik_str']).zfill(10) for v in raw_map.values()}
    pd.DataFrame({'ticker': list(cik_map.keys()),
                  'cik':    list(cik_map.values())}).to_parquet(CIK_CACHE)
    print('CIK map: ' + str(len(cik_map)) + ' entries\n')

# ══════════════════════════════════════════════════════════════════════
# PHASE 1B: EDGAR XBRL FUNDAMENTALS
# ══════════════════════════════════════════════════════════════════════
if not force_fund and FUND_PATH.exists():
    print('[CACHE] Loading ' + FUND_PATH.name)
    fundamentals_df = pd.read_parquet(FUND_PATH)
    sigs = int(fundamentals_df['has_any_3yr_signal'].sum())
    print('  ' + str(len(fundamentals_df)) + ' records | ' +
          str(fundamentals_df['ticker'].nunique()) + ' tickers | ' +
          str(sigs) + ' signal quarters\n')
else:
    print('PHASE 1: Pulling SEC EDGAR XBRL quarterly fundamentals...')
    print('-' * 60)
    records = []
    failed  = []

    for i, ticker in enumerate(tickers, 1):
        cik = cik_map.get(ticker.upper()) or cik_map.get(ticker)
        if not cik:
            failed.append(ticker)
            print('  [' + str(i).rjust(3) + '/' + str(len(tickers)) + '] ' +
                  ticker.ljust(6) + ' -> no CIK')
            continue

        df = pull_edgar(ticker, cik)
        if df is None or len(df) < 5:
            failed.append(ticker)
            print('  [' + str(i).rjust(3) + '/' + str(len(tickers)) + '] ' +
                  ticker.ljust(6) + ' -> skip')
        else:
            records.append(df)
            n_sig = int(df['has_any_3yr_signal'].sum())
            ng    = int(df['gross_3yr_high'].sum())
            no_   = int(df['operating_3yr_high'].sum())
            print('  [' + str(i).rjust(3) + '/' + str(len(tickers)) + '] ' +
                  ticker.ljust(6) +
                  ' -> ' + str(len(df)).rjust(2) + ' qtrs | ' +
                  str(n_sig) + ' signals (g:' + str(ng) + ' o:' + str(no_) + ')')

        time.sleep(EDGAR_DELAY)

    if not records:
        print('ERROR: No EDGAR data collected.')
        sys.exit(1)

    fundamentals_df = pd.concat(records, ignore_index=True)
    fundamentals_df.to_parquet(FUND_PATH)
    sigs = int(fundamentals_df['has_any_3yr_signal'].sum())
    print('\nSaved ' + FUND_PATH.name + ':')
    print('  ' + str(len(fundamentals_df)) + ' records | ' +
          str(fundamentals_df['ticker'].nunique()) + ' tickers | ' +
          str(sigs) + ' signal quarters')
    if failed:
        (DATA_DIR / 'failed_fund.txt').write_text('\n'.join(sorted(failed)))
        print('  Skipped ' + str(len(failed)) + ' tickers -> failed_fund.txt')

# ══════════════════════════════════════════════════════════════════════
# PHASE 2: ALPACA DAILY PRICES
# ══════════════════════════════════════════════════════════════════════
fund_tickers = fundamentals_df['ticker'].unique().tolist()
print('\nPHASE 2: Alpaca prices (' + PRICE_START + ' -> ' + PRICE_END + ')')
print('  ' + str(len(fund_tickers)) + ' tickers')
print('-' * 60)

failed_p = []
cached   = 0

for i, ticker in enumerate(fund_tickers, 1):
    pth = PRICES_DIR / (ticker + '.parquet')

    if not force_prices and pth.exists():
        try:
            c = pd.read_parquet(pth, columns=['close'])
            if (pd.Timestamp(PRICE_END) - c.index.max()).days <= 5:
                cached += 1
                print('  [' + str(i).rjust(3) + '/' + str(len(fund_tickers)) + '] ' +
                      ticker.ljust(6) + ' -> [CACHE] ' + str(len(c)) + ' days')
                continue
        except Exception:
            pass

    try:
        df = DataRouter.get_price_data(ticker, PRICE_START, PRICE_END,
                                       timeframe='daily', study_type='returns')
        if df is None or len(df) < 60:
            raise ValueError(str(len(df) if df is not None else 0) + ' rows')

        df.columns = [c.lower() for c in df.columns]
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        df.index = pd.to_datetime(df.index).normalize()
        df = df.sort_index()

        df['running_max'] = df['close'].cummax().shift(1)
        df['is_ath']      = (df['close'] > df['running_max']).fillna(False)

        df.to_parquet(pth)
        print('  [' + str(i).rjust(3) + '/' + str(len(fund_tickers)) + '] ' +
              ticker.ljust(6) + ' -> ' + str(len(df)) + ' days | ' +
              str(int(df['is_ath'].sum())) + ' ATH days')

    except Exception as e:
        failed_p.append(ticker)
        print('  [' + str(i).rjust(3) + '/' + str(len(fund_tickers)) + '] ' +
              ticker.ljust(6) + ' -> ERROR: ' + str(e))

if failed_p:
    (DATA_DIR / 'failed_prices.txt').write_text('\n'.join(sorted(failed_p)))

ok = len(fund_tickers) - len(failed_p)
print('\nPrices: ' + str(ok) + '/' + str(len(fund_tickers)) +
      ' (' + str(cached) + ' cached)')
print('=' * 70)
print('DONE -- next: python build_signals.py')
print('=' * 70)

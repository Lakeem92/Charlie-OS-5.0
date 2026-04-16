"""
QuantLab Macro Collector v2.0
Pulls full time-series data from FRED + yfinance for interactive charting.
Outputs: arrays for Chart.js (dates + values) plus current values and signal interpretations.
Output: catalyst_analysis_db/macro_regime/latest.json
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_collectors.collector_utils import (
    write_output, safe_api_call, parse_args
)

# ── FRED series ───────────────────────────────────────────────────────────────
FRED_SERIES = {
    # Liquidity components
    'walcl':      'WALCL',          # Fed balance sheet (weekly, millions)
    'tga':        'WDTGAL',         # Treasury General Account daily (millions)
    'rrp':        'RRPONTSYD',      # Reverse repo daily (billions)
    # Financial stress
    'nfci':       'NFCI',           # National Financial Conditions Index
    'anfci':      'ANFCI',          # Adjusted NFCI
    'stlfsi4':    'STLFSI4',        # St. Louis Financial Stress
    # Rates & plumbing
    'sofr':       'SOFR',           # Secured Overnight Financing Rate
    'effr':       'EFFR',           # Effective Fed Funds Rate
    'iorb':       'IORB',           # Interest on Reserve Balances
    'dgs10':      'DGS10',          # 10Y Treasury yield
    'dgs2':       'DGS2',           # 2Y Treasury yield
    't10y2y':     'T10Y2Y',         # 10Y-2Y spread
    't10yie':     'T10YIE',         # 10Y breakeven inflation
    # Credit
    'hy_spread':  'BAMLH0A0HYM2',   # HY OAS spread (bps)
    'drtscilm':   'DRTSCILM',       # SLOOS — % banks tightening C&I standards
    # Sentiment
    'umcsent':    'UMCSENT',        # Michigan consumer sentiment
    # Money supply
    'm2':         'WM2NS',          # M2 weekly (billions, NSA)
    'rmfns':      'RMFNS',          # Retail money market funds (billions)
    # Global dollar stress
    'swaps':      'SWPT',           # Central bank liquidity swaps
    # Real economy
    'htruckssa':  'HTRUCKSSA',      # Heavy truck sales (thousands, SA)
    'tlmfgcons':  'TLMFGCONS',      # Mfg construction spending (monthly, millions SA)
    'ipman':      'IPMAN',          # Industrial production: manufacturing (index)
    # Inflation structure
    'corestickm': 'CORESTICKM159SFRBATL',  # Sticky price CPI less shelter (% YoY)
    # Real yields
    'dfii10':     'DFII10',         # 10Y TIPS real yield
    # Commodity prices (monthly)
    'copper':     'PCOPPUSDM',      # Copper price USD/metric ton (monthly)
    # Core capex — future earnings engine
    'neworder':   'NEWORDER',       # Mfg new orders: nondefense capex ex-aircraft (monthly)
    # Bitcoin (monthly from Coinbase via FRED)
    'btc':        'CBBTCUSD',       # Bitcoin USD (monthly avg)
    # Global liquidity vortex
    'wsefintl':   'WSEFINTL1',      # Foreign custody assets at Fed (weekly, billions)
    # Shadow labor cycle
    'temphelps':  'TEMPHELPS',      # Temp help services employment (thousands)
    'payems':     'PAYEMS',         # Total nonfarm payrolls (thousands)
    # (Term premium fetched separately via _pull_term_premium — not FRED)
}

SECTOR_ETFS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLC', 'XLI', 'XLB', 'XLRE', 'XLU', 'XLP', 'XLY']
MARKET_TICKERS = ['^GSPC', '^VIX', '^VIX3M', '^RUT', 'DX-Y.NYB', 'SPY', 'GC=F', 'HG=F', 'BTC-USD'] + SECTOR_ETFS

N_DAYS = 252  # 1 year of trading days


# ── Utilities ─────────────────────────────────────────────────────────────────

def _ts(series, n=N_DAYS):
    """Convert pandas Series → {dates: [...], values: [...]} for Chart.js."""
    if series is None or len(series) == 0:
        return None
    s = series.dropna().tail(n)
    if len(s) == 0:
        return None
    return {
        'dates': [d.strftime('%Y-%m-%d') for d in s.index],
        'y': [round(float(v), 4) if abs(float(v)) < 1e9 else round(float(v), 1) for v in s.values],
    }


def _latest(series):
    """Get latest non-NaN value from a pandas Series."""
    if series is None or len(series) == 0:
        return None
    s = series.dropna()
    return round(float(s.iloc[-1]), 4) if len(s) > 0 else None


def _align(*series_list):
    """Align multiple series to common daily index with forward fill."""
    valid = [s for s in series_list if s is not None and len(s) > 0]
    if not valid:
        return [None] * len(series_list)
    all_idx = valid[0].index
    for s in valid[1:]:
        all_idx = all_idx.union(s.index)
    all_idx = all_idx.sort_values()
    result = []
    for s in series_list:
        if s is not None and len(s) > 0:
            result.append(s.reindex(all_idx).ffill().dropna())
        else:
            result.append(None)
    return result


# ── Data Pulls ────────────────────────────────────────────────────────────────

def _pull_fred():
    """Pull all FRED series as raw pandas Series (~500 calendar days)."""
    from shared.config.api_clients import FREDClient
    fred = FREDClient()
    end = datetime.now()
    start = end - timedelta(days=600)
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')

    raw = {}
    for key, fid in FRED_SERIES.items():
        result = safe_api_call(
            fred.get_series, fid,
            start_date=start_str, end_date=end_str,
            default=None, label=f'FRED {fid}'
        )
        if result is not None and len(result) > 0:
            raw[key] = result
    return raw


def _pull_market():
    """Pull yfinance close prices for market tickers (1 year)."""
    import yfinance as yf
    raw = safe_api_call(
        yf.download, MARKET_TICKERS,
        period='1y', auto_adjust=True, progress=False, threads=True,
        default=None, label='yfinance market data'
    )
    if raw is None or raw.empty:
        return {}
    close = raw['Close'] if 'Close' in raw.columns else raw
    out = {}
    for t in MARKET_TICKERS:
        if t in close.columns:
            s = close[t].dropna()
            if len(s) > 0:
                out[t] = s
    return out


# ── Derived Series ────────────────────────────────────────────────────────────

def _pull_rate_cut_odds():
    """Pull Fed rate cut probabilities from Polymarket Gamma API.

    Searches for active FOMC-related markets by liquidity, extracts
    cut/hold/hike probabilities for the next meeting.
    Returns dict with cut_pct, hold_pct, hike_pct, meeting_label, source.
    """
    import requests

    # Find top liquid Fed/rate markets
    try:
        r = requests.get(
            'https://gamma-api.polymarket.com/markets',
            params={'limit': 500, 'active': 'true', 'closed': 'false',
                    'order': 'liquidityNum', 'ascending': 'false'},
            timeout=15
        )
        all_markets = r.json() if isinstance(r.json(), list) else []
    except Exception:
        all_markets = []

    FED_KEYWORDS = ['fed ', 'fomc', 'rate cut', 'bps', 'basis point', 'interest rate',
                    'federal reserve', 'decrease interest', 'increase interest']

    fed_markets = [
        m for m in all_markets
        if any(kw in m.get('question', '').lower() for kw in FED_KEYWORDS)
    ]

    if not fed_markets:
        return {}

    # Find the "next meeting" cut markets — look for a set with matching meeting label
    # Group by meeting reference (e.g. "April 2026 meeting")
    import re
    meeting_groups = {}
    for m in fed_markets:
        q = m.get('question', '')
        # Extract meeting reference like "April 2026 meeting" or "June 2026"
        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', q)
        if date_match:
            key = date_match.group(0)
            meeting_groups.setdefault(key, []).append(m)

    if not meeting_groups:
        return {}

    # Use the meeting group with most markets (most coverage = next meeting)
    best_label = max(meeting_groups, key=lambda k: len(meeting_groups[k]))
    group = meeting_groups[best_label]

    # Parse probabilities
    cut_25_pct = None
    cut_50_pct = None
    hike_pct = None
    hold_pct_direct = None

    for m in group:
        q = m.get('question', '').lower()
        prices_raw = m.get('outcomePrices', [])
        # outcomePrices may be a JSON-encoded string or already a list
        if isinstance(prices_raw, str):
            import json as _json
            try:
                prices_raw = _json.loads(prices_raw)
            except Exception:
                continue
        if not prices_raw:
            continue
        try:
            yes_prob = float(prices_raw[0]) * 100  # first outcome = YES
        except (ValueError, IndexError):
            continue

        if 'decrease' in q and '50' in q:
            cut_50_pct = round(yes_prob, 1)
        elif 'decrease' in q and '25' in q and '50' not in q:
            cut_25_pct = round(yes_prob, 1)
        elif ('increase' in q or 'hike' in q) and 'decrease' not in q:
            hike_pct = round(yes_prob, 1)
        elif 'no change' in q:
            hold_pct_direct = round(yes_prob, 1)

    total_cut = round((cut_25_pct or 0) + (cut_50_pct or 0), 1)
    # Use direct hold market probability if available, else calculate
    hold_pct = hold_pct_direct if hold_pct_direct is not None else round(max(0, 100 - total_cut - (hike_pct or 0)), 1)

    # Regime implication
    if total_cut >= 80:
        regime_implication = 'CUT FULLY PRICED — dovish pivot imminent. Risk-on tailwind, especially growth/tech.'
        regime_color = 'green'
    elif total_cut >= 50:
        regime_implication = 'CUT LIKELY — market expects easing. Bonds bid, dollar soft, equity support.'
        regime_color = 'green'
    elif total_cut >= 25:
        regime_implication = 'CUT POSSIBLE but uncertain — mixed signals. Watch data for conviction.'
        regime_color = 'yellow'
    else:
        regime_implication = 'HOLD/HIKE EXPECTED — no imminent easing. Risk asset headwind if growth slows.'
        regime_color = 'red'

    return {
        'meeting': best_label,
        'cut_25_pct': cut_25_pct,
        'cut_50_pct': cut_50_pct,
        'hike_pct': hike_pct,
        'hold_pct': hold_pct,
        'total_cut_pct': total_cut,
        'regime_implication': regime_implication,
        'regime_color': regime_color,
        'source': 'Polymarket',
        'n_markets': len(group),
    }


def _pull_cot():
    """Pull CFTC COT data for ES (S&P 500 E-mini) and key commodities.

    Financial futures (ES): fut_fin_xls_YYYY.zip — uses Lev_Money columns.
    Disaggregated futures (GC,SI,HG,CL): fut_disagg_xls_YYYY.zip — uses M_Money columns.
    Returns dict of {instrument: pd.Series} with net speculative positioning.
    """
    import io, zipfile, requests

    # {code: (url_type, long_col, short_col)}
    FIN_TARGETS = {
        'ES': ('13874+', 'Lev_Money_Positions_Long_All', 'Lev_Money_Positions_Short_All'),
    }
    DISAGG_TARGETS = {
        'GC':      ('088691', 'M_Money_Positions_Long_ALL',        'M_Money_Positions_Short_ALL'),
        'GC_COMM': ('088691', 'Prod_Merc_Positions_Long_ALL',       'Prod_Merc_Positions_Short_ALL'),  # Gold commercials (miners/refiners)
        'SI':      ('084691', 'M_Money_Positions_Long_ALL',        'M_Money_Positions_Short_ALL'),
        'HG':      ('085692', 'M_Money_Positions_Long_ALL',        'M_Money_Positions_Short_ALL'),
        'CL': ('067651', 'M_Money_Positions_Long_ALL', 'M_Money_Positions_Short_ALL'),
    }

    results = {}
    current_year = datetime.now().year
    years = [current_year, current_year - 1]

    def _fetch_xls(url):
        r = requests.get(url, timeout=25)
        if r.status_code != 200:
            return None
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            fname = z.namelist()[0]
            with z.open(fname) as f:
                return pd.read_excel(io.BytesIO(f.read()), engine='xlrd')

    def _extract_components(df, targets):
        date_col = 'Report_Date_as_MM_DD_YYYY'
        if date_col not in df.columns:
            return
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
        code_col = 'CFTC_Contract_Market_Code'
        if code_col not in df.columns:
            return
        for key, (code, lcol, scol) in targets.items():
            sub = df[df[code_col].astype(str).str.strip() == code]
            if sub.empty or lcol not in sub.columns or scol not in sub.columns:
                continue
            longs  = sub[lcol].astype(float)
            shorts = sub[scol].astype(float)
            if key not in results:
                results[key] = {'longs': longs, 'shorts': shorts}
            else:
                results[key]['longs']  = pd.concat([results[key]['longs'],  longs ]).sort_index().drop_duplicates()
                results[key]['shorts'] = pd.concat([results[key]['shorts'], shorts]).sort_index().drop_duplicates()

    for year in years:
        try:
            df_fin = _fetch_xls(f'https://www.cftc.gov/files/dea/history/fut_fin_xls_{year}.zip')
            if df_fin is not None:
                _extract_components(df_fin, FIN_TARGETS)
        except Exception as e:
            print(f"  ⚠ COT fin {year}: {e}")
        try:
            df_dis = _fetch_xls(f'https://www.cftc.gov/files/dea/history/fut_disagg_xls_{year}.zip')
            if df_dis is not None:
                _extract_components(df_dis, DISAGG_TARGETS)
        except Exception as e:
            print(f"  ⚠ COT disagg {year}: {e}")

    cutoff = pd.Timestamp.now() - pd.Timedelta(days=730)
    out = {}
    for key, comp in results.items():
        longs  = comp['longs'][comp['longs'].index   >= cutoff].dropna()
        shorts = comp['shorts'][comp['shorts'].index >= cutoff].dropna()
        if len(longs) >= 4:
            out[key] = {'longs': longs, 'shorts': shorts}
    return out


def _compute_net_liquidity(fred_raw):
    """Net Liquidity = WALCL - TGA - RRP.  WALCL & TGA are millions → billions.
    RRP is optional — if unavailable, uses WALCL - TGA as approximation."""
    walcl = fred_raw.get('walcl')
    tga = fred_raw.get('tga')
    rrp = fred_raw.get('rrp')
    if walcl is None or tga is None:
        return None, {}
    walcl_b = walcl / 1000
    tga_b = tga / 1000
    if rrp is not None:
        rrp_b = rrp  # already billions
        w, t, r = _align(walcl_b, tga_b, rrp_b)
        if w is None:
            return None, {}
        start = max(w.index[0], t.index[0], r.index[0])
        w, t, r = w[start:], t[start:], r[start:]
        net = w - t - r
    else:
        # RRP unavailable — approximate with WALCL - TGA
        aligned = _align(walcl_b, tga_b)
        w, t = aligned[0], aligned[1]
        if w is None:
            return None, {}
        r = None
        start = max(w.index[0], t.index[0])
        w, t = w[start:], t[start:]
        net = w - t
    # Enhanced: add 20d MA, 4-week (20d) ROC, regime
    ma20 = net.rolling(20, min_periods=5).mean()
    roc_4w = ((net / net.shift(20)) - 1) * 100  # 20 trading days ≈ 4 weeks
    cur = _latest(net)
    cur_ma = _latest(ma20)
    cur_roc = _latest(roc_4w)
    regime = 'EXPANDING' if (cur_roc is not None and cur_roc > 0) else 'CONTRACTING'
    regime_color = 'green' if regime == 'EXPANDING' else 'red'
    return net, {
        'walcl': w, 'tga': t, 'rrp': r,
        'ma20': ma20,
        'roc_4w': roc_4w,
        'regime': regime,
        'regime_color': regime_color,
        'current_T': round(cur / 1000, 2) if cur else None,  # in $T
        'roc_4w_current': round(cur_roc, 2) if cur_roc else None,
        'walcl_current_T': round(_latest(w) / 1000, 2) if _latest(w) else None,
        'tga_current_B': round(_latest(t), 1) if _latest(t) else None,
        'rrp_current_B': round(_latest(r), 1) if (r is not None and _latest(r)) else None,
    }


def _compute_xly_xlp(market_raw):
    """XLY/XLP ratio + 20d MA + 5d ROC."""
    xly = market_raw.get('XLY')
    xlp = market_raw.get('XLP')
    if xly is None or xlp is None:
        return None
    xly_a, xlp_a = _align(xly, xlp)
    if xly_a is None or xlp_a is None:
        return None
    ratio = xly_a / xlp_a
    ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
    ma20 = ratio.rolling(20).mean()
    roc_5d = (ratio / ratio.shift(5) - 1) * 100

    cur_ratio = _latest(ratio)
    cur_ma = _latest(ma20)
    cur_roc = _latest(roc_5d)

    signal = 'RISK-ON' if (cur_ratio and cur_ma and cur_ratio > cur_ma) else 'RISK-OFF'
    return {
        'ratio_series': _ts(ratio),
        'ma20_series': _ts(ma20),
        'roc_series': _ts(roc_5d),
        'current_ratio': cur_ratio,
        'current_ma': cur_ma,
        'current_roc': cur_roc,
        'signal': signal,
    }


def _compute_sofr_iorb_spread(fred_raw):
    """SOFR - IORB spread (should be near zero or slightly negative in ample-reserves)."""
    sofr = fred_raw.get('sofr')
    iorb = fred_raw.get('iorb')
    if sofr is None or iorb is None:
        return None
    s, i = _align(sofr, iorb)
    if s is None or i is None:
        return None
    spread = (s - i) * 100  # convert to bps
    return spread


def _compute_sector_relative(market_raw):
    """Sector ETFs normalized to first day = 100, relative to SPY."""
    spy = market_raw.get('SPY')
    if spy is None:
        return {}
    sectors = {}
    for etf in SECTOR_ETFS:
        s = market_raw.get(etf)
        if s is None:
            continue
        spy_a, etf_a = _align(spy, s)
        if spy_a is None or etf_a is None:
            continue
        # Relative performance: (ETF / ETF[0]) / (SPY / SPY[0]) * 100
        spy_norm = spy_a / float(spy_a.iloc[0]) * 100
        etf_norm = etf_a / float(etf_a.iloc[0]) * 100
        rel = etf_norm - spy_norm  # relative outperformance in percentage points
        sectors[etf] = _ts(rel)
    return sectors


# ── Regime Classification ─────────────────────────────────────────────────────

def _classify_regime(fred_raw, market_raw):
    """Score-based regime classification."""
    vix_price = _latest(market_raw.get('^VIX'))
    hy = _latest(fred_raw.get('hy_spread'))
    t10y2y = _latest(fred_raw.get('t10y2y'))
    anfci = _latest(fred_raw.get('anfci'))
    stlfsi = _latest(fred_raw.get('stlfsi4'))

    score = 0
    details = []

    if vix_price is not None:
        if vix_price < 15:
            score += 2; details.append(f'VIX {vix_price:.1f} → Complacent (+2)')
        elif vix_price < 20:
            score += 1; details.append(f'VIX {vix_price:.1f} → Normal (+1)')
        elif vix_price < 30:
            score -= 1; details.append(f'VIX {vix_price:.1f} → Elevated (-1)')
        else:
            score -= 2; details.append(f'VIX {vix_price:.1f} → Extreme Fear (-2)')

    if hy is not None:
        if hy < 3.5:
            score += 2; details.append(f'HY Spread {hy:.0f}bp → Tight (+2)')
        elif hy < 5.0:
            score += 1; details.append(f'HY Spread {hy:.0f}bp → Normal (+1)')
        elif hy < 6.5:
            score -= 1; details.append(f'HY Spread {hy:.0f}bp → Wide (-1)')
        else:
            score -= 2; details.append(f'HY Spread {hy:.0f}bp → Stress (-2)')

    if t10y2y is not None:
        if t10y2y > 0.5:
            score += 1; details.append(f'Yield Curve {t10y2y:+.2f} → Steep (+1)')
        elif t10y2y < -0.3:
            score -= 1; details.append(f'Yield Curve {t10y2y:+.2f} → Inverted (-1)')

    if anfci is not None:
        if anfci < -0.5:
            score += 2; details.append(f'ANFCI {anfci:.2f} → Very Loose (+2)')
        elif anfci < -0.3:
            score += 1; details.append(f'ANFCI {anfci:.2f} → Loose (+1)')
        elif anfci > 0.3:
            score -= 1; details.append(f'ANFCI {anfci:.2f} → Tight (-1)')

    if stlfsi is not None:
        if stlfsi > 1.0:
            score -= 2; details.append(f'STLFSI {stlfsi:.2f} → High Stress (-2)')
        elif stlfsi > 0:
            score -= 1; details.append(f'STLFSI {stlfsi:.2f} → Mild Stress (-1)')
        else:
            score += 1; details.append(f'STLFSI {stlfsi:.2f} → Calm (+1)')

    if score >= 5:
        regime, css, icon = 'EXPANSION', 'expansion', '🟢'
    elif score >= 3:
        regime, css, icon = 'NEUTRAL-BULLISH', 'neutral', '⚪'
    elif score >= 0:
        regime, css, icon = 'NEUTRAL', 'neutral', '⚪'
    elif score >= -3:
        regime, css, icon = 'STRESS', 'stress', '🟡'
    else:
        regime, css, icon = 'CONTRACTION', 'contraction', '🔴'

    return {
        'regime': regime, 'css_class': css, 'icon': icon,
        'score': score, 'details': details,
    }


# ── Signal Interpretations ────────────────────────────────────────────────────

def _generate_signals(fred_raw, market_raw, net_liq, xly_xlp, regime):
    """Generate plain-English signal interpretation for each panel."""
    signals = {}

    # Net Liquidity
    if net_liq is not None and len(net_liq) > 20:
        cur = float(net_liq.iloc[-1])
        prev_20 = float(net_liq.iloc[-21])
        delta = cur - prev_20
        direction = 'EXPANDING' if delta > 0 else 'CONTRACTING'
        color = 'green' if delta > 0 else 'red'
        signals['net_liquidity'] = {
            'text': f'{direction} — Net Liquidity ${cur:,.0f}B, changed {delta:+,.0f}B over 20 days. '
                    f'{"TGA drawdown / RRP decline injecting cash → tailwind for risk." if delta > 0 else "TGA refill / QT draining reserves → headwind for risk."}',
            'color': color, 'direction': direction,
        }

    # XLY/XLP Risk Appetite
    if xly_xlp:
        sig = xly_xlp['signal']
        roc = xly_xlp.get('current_roc')
        ratio = xly_xlp.get('current_ratio')
        color = 'green' if sig == 'RISK-ON' else 'red'
        roc_text = f'5d ROC: {roc:+.2f}%' if roc is not None else ''
        signals['xly_xlp'] = {
            'text': f'{sig} — XLY/XLP ratio {"above" if sig == "RISK-ON" else "below"} 20d MA. '
                    f'Consumer discretionary {"outperforming" if sig == "RISK-ON" else "underperforming"} staples. {roc_text}',
            'color': color, 'direction': sig,
        }

    # VIX Structure
    vix = _latest(market_raw.get('^VIX'))
    vix3m = _latest(market_raw.get('^VIX3M'))
    if vix is not None and vix3m is not None and vix3m > 0:
        ratio = vix / vix3m
        if ratio > 1.05:
            signals['vix'] = {'text': f'BACKWARDATION — VIX/VIX3M {ratio:.3f}. Near-term fear exceeds medium-term → panic events active.', 'color': 'red', 'direction': 'BACKWARDATION'}
        elif ratio > 0.95:
            signals['vix'] = {'text': f'FLAT — VIX/VIX3M {ratio:.3f}. Term structure neutral. No directional bias from vol.', 'color': 'yellow', 'direction': 'FLAT'}
        else:
            signals['vix'] = {'text': f'CONTANGO — VIX/VIX3M {ratio:.3f}. Healthy term structure. Near-term complacency.', 'color': 'green', 'direction': 'CONTANGO'}

    # SOFR-IORB Spread
    sofr = _latest(fred_raw.get('sofr'))
    iorb = _latest(fred_raw.get('iorb'))
    if sofr is not None and iorb is not None:
        spread_bps = (sofr - iorb) * 100
        if spread_bps > 2:
            signals['rates'] = {'text': f'SCARCE RESERVES — SOFR-IORB spread at {spread_bps:+.0f}bp. Funding stress building. Cash premium in repo.', 'color': 'red', 'direction': 'STRESS'}
        elif spread_bps < -2:
            signals['rates'] = {'text': f'AMPLE RESERVES — SOFR-IORB spread at {spread_bps:+.0f}bp. Banks flush with cash. No funding friction.', 'color': 'green', 'direction': 'AMPLE'}
        else:
            signals['rates'] = {'text': f'NORMAL PLUMBING — SOFR-IORB spread at {spread_bps:+.0f}bp. Reserves adequate. No stress signal.', 'color': 'yellow', 'direction': 'NORMAL'}

    # Financial Stress
    anfci = _latest(fred_raw.get('anfci'))
    nfci = _latest(fred_raw.get('nfci'))
    stlfsi = _latest(fred_raw.get('stlfsi4'))
    stress_vals = [v for v in [anfci, nfci, stlfsi] if v is not None]
    if stress_vals:
        avg_stress = sum(stress_vals) / len(stress_vals)
        if avg_stress > 0.3:
            signals['stress'] = {'text': f'ELEVATED STRESS — Financial conditions tightening (ANFCI: {anfci}, NFCI: {nfci}, STLFSI: {stlfsi}). Credit/funding friction rising.', 'color': 'red', 'direction': 'TIGHT'}
        elif avg_stress < -0.3:
            signals['stress'] = {'text': f'LOOSE — Financial conditions accommodative (ANFCI: {anfci}, NFCI: {nfci}, STLFSI: {stlfsi}). Risk-on environment.', 'color': 'green', 'direction': 'LOOSE'}
        else:
            signals['stress'] = {'text': f'NEUTRAL — Financial conditions near average (ANFCI: {anfci}, NFCI: {nfci}, STLFSI: {stlfsi}).', 'color': 'yellow', 'direction': 'NEUTRAL'}

    # M2 Money Supply
    m2 = fred_raw.get('m2')
    if m2 is not None and len(m2) > 52:
        cur_m2 = float(m2.iloc[-1])
        yr_ago = float(m2.iloc[-52]) if len(m2) >= 52 else float(m2.iloc[0])
        m2_yoy = (cur_m2 / yr_ago - 1) * 100
        color = 'green' if m2_yoy > 0 else 'red'
        signals['m2'] = {'text': f'M2 at ${cur_m2/1000:,.1f}T — YoY change: {m2_yoy:+.1f}%. {"Money supply expanding → supports asset prices." if m2_yoy > 0 else "Money supply contracting → deflationary pressure on assets."}', 'color': color, 'direction': 'EXPANDING' if m2_yoy > 0 else 'CONTRACTING'}

    return signals


# ── COT Entry Builder ─────────────────────────────────────────────────────────

def _build_cot_entry(comp):
    """Build COT data dict with separate longs/shorts, 20-week MA, COT index, and trajectory."""
    longs  = comp['longs']
    shorts = comp['shorts']
    net    = (longs - shorts).dropna()

    current_l = round(float(longs.iloc[-1]),  0) if len(longs)  >= 1 else None
    current_s = round(float(shorts.iloc[-1]), 0) if len(shorts) >= 1 else None
    current   = round(float(net.iloc[-1]),    0) if len(net)    >= 1 else None
    chg_l = round(float(longs.iloc[-1])  - float(longs.iloc[-2]),  0) if len(longs)  >= 2 else None
    chg_s = round(float(shorts.iloc[-1]) - float(shorts.iloc[-2]), 0) if len(shorts) >= 2 else None
    chg   = round(float(net.iloc[-1])    - float(net.iloc[-2]),    0) if len(net)    >= 2 else None

    # 4-week ROC on net
    roc_4w = None
    if len(net) >= 5 and net.iloc[-5] != 0:
        roc_4w = round((float(net.iloc[-1]) - float(net.iloc[-5])) / abs(float(net.iloc[-5])) * 100, 1)

    # COT Index: 0-100 oscillator (52-week range of net)
    cot_index = None
    window = min(len(net), 52)
    if window >= 10:
        net_w = net.tail(window)
        rng = float(net_w.max() - net_w.min())
        if rng > 0:
            cot_index = round((float(net.iloc[-1]) - float(net_w.min())) / rng * 100, 1)

    # 20-week MA series for longs and shorts
    def _ma20(s):
        ma = s.rolling(20, min_periods=5).mean()
        return _ts(ma, n=104)

    # Trajectory
    trajectory = None
    if current is not None and chg is not None:
        heavy_short = current < -50000
        heavy_long  = current > 50000
        if heavy_short and chg > 0:
            trajectory = 'SHORT SQUEEZE POSSIBLE'
        elif heavy_short:
            trajectory = 'SHORT BUILDING'
        elif heavy_long and chg < 0:
            trajectory = 'LONG UNWIND RISK'
        elif heavy_long:
            trajectory = 'LONG BUILDING'
        elif current > 0 and chg < 0:
            trajectory = 'LONGS FADING'
        elif current < 0 and chg > 0:
            trajectory = 'SHORTS COVERING'
        elif current > 0:
            trajectory = 'NET LONG'
        else:
            trajectory = 'NET SHORT'

    return {
        'longs_series':  _ts(longs,  n=104),
        'shorts_series': _ts(shorts, n=104),
        'net_series':    _ts(net,    n=104),
        'longs_ma20':    _ma20(longs),
        'shorts_ma20':   _ma20(shorts),
        'current': current, 'current_l': current_l, 'current_s': current_s,
        'chg': chg, 'chg_l': chg_l, 'chg_s': chg_s,
        'roc_4w': roc_4w,
        'cot_index': cot_index,
        'trajectory': trajectory,
    }


# ── Yield Curve ROC ───────────────────────────────────────────────────────────

def _yield_curve_roc(series):
    """Compute 4-week ROC of the 10Y-2Y spread (in bp change, not %)."""
    if series is None or len(series) < 20:
        return None
    try:
        recent = float(series.iloc[-1])
        prior  = float(series.iloc[-20])   # ~4 weeks of daily data
        return round(recent - prior, 3)    # absolute change in pp
    except Exception:
        return None


# ── NY Fed Term Premium (ACM model) ──────────────────────────────────────────

def _pull_term_premium():
    """Download ACM 10Y term premium directly from NY Fed Excel file."""
    import io, requests
    url = 'https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls'
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        df = pd.read_excel(io.BytesIO(r.content), engine='xlrd')
        # Date column is first, ACMTP10 is the 10Y term premium column
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
        col = 'ACMTP10' if 'ACMTP10' in df.columns else df.columns[1]
        series = df[col].astype(float).dropna()
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=365 * 10)
        return series[series.index >= cutoff]
    except Exception as e:
        print(f"  ⚠ Term premium fetch failed: {e}")
        return None


# ── Computed ratio series ─────────────────────────────────────────────────────

def _fetch_spx_eps_estimates():
    """Build Yardeni-style S&P 500 EPS growth chart.
    Uses yfinance quarterly earnings for bellwethers; groups by Q1/Q2/Q3/Q4.
    Returns per-quarter YoY EPS growth series so Chart.js can draw one line per quarter.
    Benzinga (if key available) supplements with forward estimates.
    """
    import yfinance as yf
    import os, requests
    from dotenv import load_dotenv
    from collections import defaultdict

    # Bellwether basket — mega-cap S&P 500 constituents with consistent reporting
    BASKET = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'JPM', 'V', 'UNH', 'XOM']

    # Map quarter-end month → Q label
    def _qlabel(dt):
        m = dt.month
        y = dt.year
        q = {3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4'}.get(m)
        return f"{q}-{y}" if q else None

    # Collect (quarter_label, year, qnum) → [eps_yoy_growth, ...]
    quarterly_by_ticker = {}
    for ticker in BASKET:
        try:
            t = yf.Ticker(ticker)
            df = t.quarterly_income_stmt
            if df is None or df.empty:
                continue
            # Find EPS rows — try multiple label variants
            eps_row = None
            for label in ['Basic EPS', 'Diluted EPS', 'Basic Earnings Per Share', 'Diluted Earnings Per Share']:
                if label in df.index:
                    eps_row = df.loc[label]
                    break
            if eps_row is None:
                continue
            eps_row = eps_row.dropna().sort_index()
            quarterly_by_ticker[ticker] = eps_row
        except Exception:
            continue

    if not quarterly_by_ticker:
        return None

    # Build YoY growth per quarter across basket
    # For each ticker, compute YoY EPS growth for each quarter, then average across basket
    # Structure: {quarter_label: [(date, yoy_growth), ...]}
    quarter_growth = defaultdict(list)   # 'Q1' → [(date, avg_yoy), ...]

    for ticker, eps_series in quarterly_by_ticker.items():
        dates = list(eps_series.index)
        vals  = list(eps_series.values)
        for i, (d, v) in enumerate(zip(dates, vals)):
            # Find same quarter 1 year ago
            yr_ago = None
            for j, d2 in enumerate(dates):
                if d2.month == d.month and abs((d - d2).days - 365) < 50:
                    yr_ago = vals[j]
                    break
            if yr_ago is None or yr_ago == 0 or v is None:
                continue
            try:
                yoy = float((float(v) / float(yr_ago) - 1) * 100)
                if abs(yoy) > 200:  # filter outliers
                    continue
                ql = _qlabel(d)
                if ql:
                    quarter_growth[ql].append((d, yoy))
            except (TypeError, ValueError, ZeroDivisionError):
                continue

    if not quarter_growth:
        return None

    # For each Q label, compute the average YoY growth across basket tickers
    # Build per-Qtype lines: 'Q1', 'Q2', 'Q3', 'Q4' each as time series
    q_lines = {}
    for ql, pairs in sorted(quarter_growth.items(), key=lambda x: x[0]):
        pairs.sort(key=lambda x: x[0])
        # Use latest date for this quarter
        latest_date, latest_growth = pairs[-1]
        qtype = ql[:2]  # 'Q1', 'Q2', 'Q3', 'Q4'
        year  = int(ql[3:])
        if qtype not in q_lines:
            q_lines[qtype] = []
        q_lines[qtype].append({'label': ql, 'year': year, 'yoy': round(latest_growth, 2)})

    # Sort each line's data by year
    for qtype in q_lines:
        q_lines[qtype].sort(key=lambda x: x['year'])

    # ── Benzinga: forward estimates for this + next quarter ─────────────────
    fwd_by_quarter = {}
    load_dotenv(r'C:\QuantLab\Data_Lab\.env')
    token = os.getenv('BENZINGA_API_KEY')
    if token:
        today  = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=120)).strftime('%Y-%m-%d')
        url    = 'https://api.benzinga.com/api/v2.1/calendar/earnings'
        params = {'token': token, 'importance': '4', 'date_from': today, 'date_to': future, 'pagesize': '100'}
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                for e in r.json().get('earnings', []):
                    date_str = e.get('date', '')
                    eps_est  = e.get('eps_est')
                    if not date_str or eps_est in (None, '', 'N/A'):
                        continue
                    try:
                        dt = pd.Timestamp(date_str)
                        ql = _qlabel(dt)
                        if ql:
                            fwd_by_quarter.setdefault(ql, []).append(float(eps_est))
                    except (TypeError, ValueError):
                        continue
        except Exception:
            pass

    # Build flat chronological series for bar chart
    q_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    series = []
    for qtype, items in q_lines.items():
        for item in items:
            series.append({**item, 'qtype': qtype})
    series.sort(key=lambda x: (x['year'], q_order.get(x['qtype'], 0)))

    return {
        'q_lines': q_lines,
        'series':  series,      # flat chronological list [{label, year, qtype, yoy}, ...]
        'fwd_bz':  fwd_by_quarter,
        'basket':  BASKET,
        'latest':  series[-1] if series else None,
        'prior':   series[-2] if len(series) >= 2 else None,
    }


def _compute_onshoring_ratio(fred_raw):
    """TLMFGCONS / IPMAN — capex vs output efficiency."""
    cons = fred_raw.get('tlmfgcons')
    prod = fred_raw.get('ipman')
    if cons is None or prod is None:
        return None
    combined = pd.DataFrame({'cons': cons, 'prod': prod}).dropna()
    if len(combined) < 6:
        return None
    ratio = combined['cons'] / combined['prod']
    return ratio


def _compute_temp_help_ratio(fred_raw):
    """TEMPHELPS / PAYEMS — temp workers as share of total payrolls."""
    t = fred_raw.get('temphelps')
    p = fred_raw.get('payems')
    if t is None or p is None:
        return None
    df = pd.DataFrame({'t': t, 'p': p}).dropna()
    if len(df) < 6:
        return None
    return (df['t'] / df['p']) * 100   # express as % of total payrolls


def _compute_copper_gold_ratio(market_raw):
    """Copper futures / Gold futures — growth vs fear ratio (daily via yfinance)."""
    copper = market_raw.get('HG=F')
    gold   = market_raw.get('GC=F')
    if copper is None or gold is None:
        return None
    combined = pd.DataFrame({'copper': copper, 'gold': gold}).dropna()
    if len(combined) < 6:
        return None
    # HG=F is in USD/lb, GC=F is in USD/troy oz — ratio is unitless
    return combined['copper'] / combined['gold']


def _roc_4w(series):
    """4-period ROC% on a series (works for weekly or monthly)."""
    if series is None or len(series) < 5:
        return None
    try:
        prev = float(series.iloc[-5])
        if prev == 0:
            return None
        return round((float(series.iloc[-1]) / prev - 1) * 100, 2)
    except Exception:
        return None


def _roc_12m(series):
    """12-period (year-over-year) ROC% — for monthly series."""
    if series is None or len(series) < 13:
        return None
    try:
        prev = float(series.iloc[-13])
        if prev == 0:
            return None
        return round((float(series.iloc[-1]) / prev - 1) * 100, 2)
    except Exception:
        return None


# ── RSI Computation ───────────────────────────────────────────────────────────

def _compute_rsi(series, period=14):
    """Standard 14-period RSI on a pandas Series. Returns Series."""
    if series is None or len(series) < period + 1:
        return None
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, float('nan'))
    return (100 - 100 / (1 + rs)).dropna()


# ── CBOE Put/Call Ratio ────────────────────────────────────────────────────────

def _pull_pcr():
    """Pull CBOE total put/call ratio history. Returns pd.Series indexed by date."""
    import requests, io
    url = 'https://cdn.cboe.com/api/global/us_indices/daily_prices/PCALL_History.csv'
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            # Columns: 'DATE' or first col, 'P/C Ratio' or similar
            df.columns = [c.strip() for c in df.columns]
            date_col = df.columns[0]
            pc_col   = df.columns[1]  # total P/C is first ratio column
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
            series = pd.to_numeric(df[pc_col], errors='coerce').dropna()
            if len(series) > 20:
                return series
    except Exception as e:
        print(f"  ⚠ CBOE P/C ratio: {e}")
    return None


# ── SPX Options Regime (VIX term structure + SPY chain) ───────────────────────

def _pull_spx_options_regime(market_raw):
    """Compute options regime from VIX term structure and SPY options chain."""
    import yfinance as yf

    vix   = _latest(market_raw.get('^VIX'))
    vix3m = _latest(market_raw.get('^VIX3M'))
    result = {'vix': vix, 'vix3m': vix3m}

    # Term structure ratio: VIX3M/VIX
    if vix and vix3m and vix > 0:
        ts_ratio = round(vix3m / vix, 3)
        result['ts_ratio'] = ts_ratio
        if ts_ratio < 0.90:
            result['ts_regime']      = 'BACKWARDATION'
            result['ts_label']       = 'FEAR'
            result['ts_implication'] = 'Near-term fear > long-term — acute stress, expect violent moves. Reduce size, widen stops, bias to short or flat.'
        elif ts_ratio < 1.0:
            result['ts_regime']      = 'MILD BACKWARDATION'
            result['ts_label']       = 'CAUTION'
            result['ts_implication'] = 'Market pricing near-term risk above average. Not panic but not clean — stay selective, use tighter entries.'
        elif ts_ratio < 1.10:
            result['ts_regime']      = 'FLAT CONTANGO'
            result['ts_label']       = 'NEUTRAL'
            result['ts_implication'] = 'Vol term structure normal. Options not flagging extreme fear or complacency. Standard momentum conditions.'
        else:
            result['ts_regime']      = 'STEEP CONTANGO'
            result['ts_label']       = 'COMPLACENCY'
            result['ts_implication'] = 'Long-term vol priced well above spot — market very calm short-term. Classic low-vol momentum environment. But watch for VIX spikes from complacency lows.'

    # VIX regime
    if vix:
        if vix < 13:
            result['vix_regime'] = 'SUPPRESSED'; result['vix_color'] = 'green'
        elif vix < 20:
            result['vix_regime'] = 'LOW'; result['vix_color'] = 'green'
        elif vix < 25:
            result['vix_regime'] = 'ELEVATED'; result['vix_color'] = 'yellow'
        elif vix < 30:
            result['vix_regime'] = 'HIGH'; result['vix_color'] = 'red'
        else:
            result['vix_regime'] = 'EXTREME'; result['vix_color'] = 'red'

    # SPY options chain — max pain + gamma regime
    try:
        spy     = yf.Ticker('SPY')
        exps    = spy.options
        if exps:
            chain   = spy.option_chain(exps[0])
            calls   = chain.calls[['strike', 'openInterest']].dropna()
            puts    = chain.puts[['strike', 'openInterest']].dropna()
            spot    = _latest(market_raw.get('SPY'))

            # Max pain: minimize total ITM payout at each strike
            all_strikes = sorted(set(calls['strike']) | set(puts['strike']))
            min_pain, max_pain_strike = float('inf'), None
            for s in all_strikes:
                cp = float((calls[calls['strike'] < s]['openInterest'] * (s - calls[calls['strike'] < s]['strike'])).sum())
                pp = float((puts[puts['strike'] > s]['openInterest'] * (puts[puts['strike'] > s]['strike'] - s)).sum())
                total = cp + pp
                if total < min_pain:
                    min_pain = total; max_pain_strike = s

            total_put_oi  = int(puts['openInterest'].sum())
            total_call_oi = int(calls['openInterest'].sum())
            pc_oi_ratio   = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else None

            result['max_pain']    = max_pain_strike
            result['spot']        = spot
            result['pc_oi']       = pc_oi_ratio
            result['put_oi']      = total_put_oi
            result['call_oi']     = total_call_oi
            result['expiry']      = exps[0]

            if spot and max_pain_strike:
                gap_pct = round((spot - max_pain_strike) / max_pain_strike * 100, 2)
                result['mp_gap_pct'] = gap_pct
                if gap_pct > 3:
                    result['gamma_regime']      = 'NEGATIVE GAMMA'
                    result['gamma_label']       = 'DEALERS SHORT GAMMA'
                    result['gamma_implication'] = f'SPY {gap_pct:+.1f}% above max pain (${max_pain_strike:.0f}). Dealers short gamma — they AMPLIFY moves in both directions. Volatility is structurally elevated. Breakouts go further, drops go deeper. Tighten stops.'
                elif gap_pct < -3:
                    result['gamma_regime']      = 'POSITIVE GAMMA'
                    result['gamma_label']       = 'DEALERS LONG GAMMA'
                    result['gamma_implication'] = f'SPY {gap_pct:+.1f}% below max pain (${max_pain_strike:.0f}). Dealers long gamma — they DAMPEN moves, selling rallies and buying dips. Range-bound conditions likely. Fade extremes, mean-reversion bias.'
                else:
                    result['gamma_regime']      = 'AT MAX PAIN'
                    result['gamma_label']       = 'PINNED'
                    result['gamma_implication'] = f'SPY within 3% of max pain (${max_pain_strike:.0f}). Gravitational pull toward this level is strong. Expect compression and potential pinning into expiry.'
    except Exception as e:
        print(f"  ⚠ SPY options regime: {e}")

    return result


# ── BTC/Gold and BTC/HY computed series ───────────────────────────────────────

def _compute_btc_gold_ratio(market_raw, fred_raw=None):
    """BTC (yfinance daily) / Gold futures (yfinance GC=F daily), resampled to monthly."""
    btc  = market_raw.get('BTC-USD')
    gold = market_raw.get('GC=F')  # Gold futures from yfinance (already pulled)
    if btc is None or gold is None:
        return None
    # Resample both to month-end
    btc_m  = btc.resample('ME').last().dropna()
    gold_m = gold.resample('ME').last().dropna()
    df = pd.DataFrame({'btc': btc_m, 'gold': gold_m}).dropna()
    if len(df) < 3:
        return None
    return df['btc'] / df['gold']


def _compute_ma(series, window=200):
    """Rolling MA on a series. Returns latest value."""
    if series is None or len(series) < window // 2:
        return None
    return series.rolling(min(window, len(series)), min_periods=max(1, window // 4)).mean()


# ── Build Sector Heatmap (table data, kept for reference) ─────────────────────

def _build_sector_heatmap(market_raw):
    """Sector rotation heatmap table rows."""
    rows = []
    spy = market_raw.get('SPY')
    for etf in SECTOR_ETFS:
        s = market_raw.get(etf)
        if s is None or len(s) < 6:
            continue
        last = float(s.iloc[-1])
        ret_5d = (last / float(s.iloc[-6]) - 1) * 100 if len(s) >= 6 else None
        ret_20d = (last / float(s.iloc[-21]) - 1) * 100 if len(s) >= 21 else None
        ret_60d = (last / float(s.iloc[-61]) - 1) * 100 if len(s) >= 61 else None
        rel_5d, rel_20d, rel_60d = None, None, None
        if spy is not None and len(spy) >= 6:
            spy_last = float(spy.iloc[-1])
            spy_5d = (spy_last / float(spy.iloc[-6]) - 1) * 100 if len(spy) >= 6 else None
            spy_20d = (spy_last / float(spy.iloc[-21]) - 1) * 100 if len(spy) >= 21 else None
            spy_60d = (spy_last / float(spy.iloc[-61]) - 1) * 100 if len(spy) >= 61 else None
            if ret_5d is not None and spy_5d is not None:
                rel_5d = round(ret_5d - spy_5d, 2)
            if ret_20d is not None and spy_20d is not None:
                rel_20d = round(ret_20d - spy_20d, 2)
            if ret_60d is not None and spy_60d is not None:
                rel_60d = round(ret_60d - spy_60d, 2)
        rows.append({
            'ticker': etf,
            'ret_5d': round(ret_5d, 2) if ret_5d else None,
            'ret_20d': round(ret_20d, 2) if ret_20d else None,
            'ret_60d': round(ret_60d, 2) if ret_60d else None,
            'rel_5d': rel_5d, 'rel_20d': rel_20d, 'rel_60d': rel_60d,
        })
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def collect():
    """Main collection: pull everything, compute derived, output JSON."""
    print("📊 Macro Collector v2 — starting...")

    print("  Pulling FRED data...")
    fred_raw = _pull_fred()
    print(f"    Got {len(fred_raw)}/{len(FRED_SERIES)} series")

    print("  Pulling yfinance data...")
    market_raw = _pull_market()
    print(f"    Got {len(market_raw)}/{len(MARKET_TICKERS)} tickers")

    print("  Pulling Fed rate cut odds...")
    rate_cut_odds = safe_api_call(_pull_rate_cut_odds, default={}, label='Polymarket rate cut odds')

    print("  Pulling CFTC COT data...")
    cot_raw = safe_api_call(_pull_cot, default={}, label='CFTC COT')

    print("  Pulling NY Fed term premium...")
    term_premium_series = safe_api_call(_pull_term_premium, default=None, label='ACM term premium')
    print(f"    Got COT for: {list(cot_raw.keys()) if cot_raw else 'none'}")

    print("  Pulling S&P 500 EPS estimates (yfinance bellwethers + Benzinga)...")
    spx_eps = safe_api_call(_fetch_spx_eps_estimates, default=None, label='SPX EPS estimates')

    # Derived
    print("  Computing derived series...")
    net_liq, liq_parts = _compute_net_liquidity(fred_raw)
    xly_xlp = _compute_xly_xlp(market_raw)
    sofr_iorb = _compute_sofr_iorb_spread(fred_raw)
    sector_rel = _compute_sector_relative(market_raw)
    onshoring_ratio   = _compute_onshoring_ratio(fred_raw)
    copper_gold_ratio = _compute_copper_gold_ratio(market_raw)
    temp_help_ratio   = _compute_temp_help_ratio(fred_raw)
    btc_gold_ratio    = _compute_btc_gold_ratio(market_raw, fred_raw)

    print("  Pulling CBOE P/C ratio...")
    pcr_series = safe_api_call(_pull_pcr, default=None, label='CBOE P/C ratio')

    print("  Pulling SPX options regime...")
    spx_options = safe_api_call(_pull_spx_options_regime, market_raw, default={}, label='SPX options regime')

    # Regime
    regime = _classify_regime(fred_raw, market_raw)
    print(f"  Regime: {regime['icon']} {regime['regime']} (score: {regime['score']})")

    # Signals
    signals = _generate_signals(fred_raw, market_raw, net_liq, xly_xlp, regime)

    # Build output
    output = {
        'regime': regime,
        'signals': signals,

        # Net Liquidity — enhanced with MA, ROC, regime
        'net_liquidity': {
            'current': _latest(net_liq),
            'series': _ts(net_liq),
            'ma20_series': _ts(liq_parts.get('ma20')),
            'roc_series': _ts(liq_parts.get('roc_4w')),
            'walcl': _ts(liq_parts.get('walcl')),
            'tga': _ts(liq_parts.get('tga')),
            'rrp': _ts(liq_parts.get('rrp')),
            'regime': liq_parts.get('regime'),
            'regime_color': liq_parts.get('regime_color'),
            'current_T': liq_parts.get('current_T'),
            'roc_4w': liq_parts.get('roc_4w_current'),
            'walcl_T': liq_parts.get('walcl_current_T'),
            'tga_B': liq_parts.get('tga_current_B'),
            'rrp_B': liq_parts.get('rrp_current_B'),
        },

        # SPX for overlay
        'spx_series': _ts(market_raw.get('^GSPC')),

        # XLY/XLP Risk Appetite
        'xly_xlp': xly_xlp,

        # VIX + term structure
        'vix': {
            'series': _ts(market_raw.get('^VIX')),
            'vix3m_series': _ts(market_raw.get('^VIX3M')),
            'current': _latest(market_raw.get('^VIX')),
            'vix3m': _latest(market_raw.get('^VIX3M')),
        },

        # Rates & plumbing
        'rates': {
            'sofr': _ts(fred_raw.get('sofr')),
            'effr': _ts(fred_raw.get('effr')),
            'iorb': _ts(fred_raw.get('iorb')),
            'dgs10': _ts(fred_raw.get('dgs10')),
            'dgs2': _ts(fred_raw.get('dgs2')),
            't10y2y': _ts(fred_raw.get('t10y2y')),
            't10y2y_roc_4w': _yield_curve_roc(fred_raw.get('t10y2y')),
            'sofr_iorb': _ts(sofr_iorb),
        },

        # Financial stress
        'stress': {
            'nfci': _ts(fred_raw.get('nfci')),
            'anfci': _ts(fred_raw.get('anfci')),
            'stlfsi4': _ts(fred_raw.get('stlfsi4')),
        },

        # M2 Money Supply
        'm2': {
            'series': _ts(fred_raw.get('m2')),
            'current': _latest(fred_raw.get('m2')),
        },

        # Sector rotation lines (relative to SPY)
        'sector_lines': sector_rel,

        # Current values for cards
        'market': {
            'spx': _latest(market_raw.get('^GSPC')),
            'rut': _latest(market_raw.get('^RUT')),
            'dxy': _latest(market_raw.get('DX-Y.NYB')),
            'spy_5d': round((float(market_raw['^GSPC'].iloc[-1]) / float(market_raw['^GSPC'].iloc[-6]) - 1) * 100, 2) if '^GSPC' in market_raw and len(market_raw['^GSPC']) >= 6 else None,
        },
        'fred_current': {
            'sofr': _latest(fred_raw.get('sofr')),
            'effr': _latest(fred_raw.get('effr')),
            'iorb': _latest(fred_raw.get('iorb')),
            'dgs10': _latest(fred_raw.get('dgs10')),
            'dgs2': _latest(fred_raw.get('dgs2')),
            't10y2y': _latest(fred_raw.get('t10y2y')),
            't10yie': _latest(fred_raw.get('t10yie')),
            'hy_spread': _latest(fred_raw.get('hy_spread')),
            'anfci': _latest(fred_raw.get('anfci')),
            'umcsent': _latest(fred_raw.get('umcsent')),
        },

        # Sector heatmap table
        'sector_heatmap': _build_sector_heatmap(market_raw),

        # Fed Rate Cut Odds — Polymarket
        'rate_cut_odds': rate_cut_odds,

        # CFTC COT — non-commercial longs/shorts/net with COT index
        'cot': {
            key: _build_cot_entry(comp)
            for key, comp in cot_raw.items()
        },

        # ── New macro signals ────────────────────────────────────────────────
        # SLOOS — credit spigot (quarterly)
        'sloos': {
            'series': _ts(fred_raw.get('drtscilm'), n=40),
            'current': _latest(fred_raw.get('drtscilm')),
        },
        # Heavy truck sales — real economy pulse (monthly)
        'heavy_trucks': {
            'series': _ts(fred_raw.get('htruckssa'), n=60),
            'current': _latest(fred_raw.get('htruckssa')),
            'prev':    round(float(fred_raw['htruckssa'].iloc[-2]), 1) if fred_raw.get('htruckssa') is not None and len(fred_raw['htruckssa']) >= 2 else None,
        },
        # Retail money market funds — dry powder gauge (weekly)
        'retail_mmf': {
            'series': _ts(fred_raw.get('rmfns'), n=104),
            'current': _latest(fred_raw.get('rmfns')),
        },
        # Sticky price CPI less shelter (monthly)
        'sticky_cpi': {
            'series': _ts(fred_raw.get('corestickm'), n=60),
            'current': _latest(fred_raw.get('corestickm')),
            'prev':    round(float(fred_raw['corestickm'].iloc[-2]), 2) if fred_raw.get('corestickm') is not None and len(fred_raw['corestickm']) >= 2 else None,
        },
        # STLFSI4 current (already in stress.stlfsi4, add scalar here for signals)
        'stlfsi4_current': _latest(fred_raw.get('stlfsi4')),

        # ── Shadow Liquidity: RRP standalone ────────────────────────────────
        'rrp_shadow': {
            'series':  _ts(fred_raw.get('rrp'), n=260),
            'current': _latest(fred_raw.get('rrp')),
            'roc_4w':  _roc_4w(fred_raw.get('rrp')),
        },

        # ── Onshoring Efficiency Ratio ───────────────────────────────────────
        'onshoring': {
            'series':       _ts(onshoring_ratio, n=60) if onshoring_ratio is not None else None,
            'current':      round(float(onshoring_ratio.iloc[-1]), 4) if onshoring_ratio is not None and len(onshoring_ratio) >= 1 else None,
            'prev':         round(float(onshoring_ratio.iloc[-2]), 4) if onshoring_ratio is not None and len(onshoring_ratio) >= 2 else None,
            'roc_4w':       _roc_4w(onshoring_ratio),
            'cons_current': _latest(fred_raw.get('tlmfgcons')),
            'prod_current': _latest(fred_raw.get('ipman')),
        },

        # ── Copper/Gold Ratio + Real Yields ─────────────────────────────────
        'copper_gold': {
            'ratio_series':       _ts(copper_gold_ratio, n=252) if copper_gold_ratio is not None else None,
            'ratio_current':      round(float(copper_gold_ratio.iloc[-1]), 6) if copper_gold_ratio is not None and len(copper_gold_ratio) >= 1 else None,
            'ratio_roc_4w':       _roc_4w(copper_gold_ratio),
            'real_yield_series':  _ts(fred_raw.get('dfii10'), n=252),
            'real_yield_current': _latest(fred_raw.get('dfii10')),
            'copper_current':     _latest(market_raw.get('HG=F')),
            'gold_current':       _latest(market_raw.get('GC=F')),
        },

        # ── Foreign Custody Assets — Global Liquidity Vortex ────────────────
        'foreign_custody': {
            'series':  _ts(fred_raw.get('wsefintl'), n=260),
            'current': _latest(fred_raw.get('wsefintl')),
            'roc_4w':  _roc_4w(fred_raw.get('wsefintl')),
        },

        # ── Temp Help Ratio — Shadow Labor Cycle ─────────────────────────────
        'temp_help': {
            'series':        _ts(temp_help_ratio, n=120),
            'current':       round(float(temp_help_ratio.iloc[-1]), 4) if temp_help_ratio is not None and len(temp_help_ratio) >= 1 else None,
            'prev':          round(float(temp_help_ratio.iloc[-2]), 4) if temp_help_ratio is not None and len(temp_help_ratio) >= 2 else None,
            'roc_12m':       _roc_12m(temp_help_ratio),
        },

        # ── Term Premium — Bond Vigilante Signal ─────────────────────────────
        'term_premium': {
            'series':  _ts(term_premium_series, n=520),
            'current': _latest(term_premium_series),
            'prev':    round(float(term_premium_series.iloc[-2]), 4) if term_premium_series is not None and len(term_premium_series) >= 2 else None,
            'roc_4w':  _roc_4w(term_premium_series),
        },

        # ── S&P 500 EPS Growth by Quarter (Yardeni-style) ────────────────────
        'spx_eps': spx_eps,

        # ── Credit Heartbeat — HY Spread dedicated panel ─────────────────
        'hy_spread': {
            'series':  _ts(fred_raw.get('hy_spread'), n=260),
            'current': _latest(fred_raw.get('hy_spread')),
            'prev':    round(float(fred_raw['hy_spread'].iloc[-2]), 4) if fred_raw.get('hy_spread') is not None and len(fred_raw['hy_spread']) >= 2 else None,
            'roc_4w':  _roc_4w(fred_raw.get('hy_spread')),
        },

        # ── Core Capex — Future Earnings Engine (NEWORDER) ───────────────
        'core_capex': {
            'series':  _ts(fred_raw.get('neworder'), n=120),
            'current': _latest(fred_raw.get('neworder')),
            'prev':    round(float(fred_raw['neworder'].iloc[-2]), 2) if fred_raw.get('neworder') is not None and len(fred_raw['neworder']) >= 2 else None,
            'roc_4w':  _roc_4w(fred_raw.get('neworder')),
            'roc_12m': _roc_12m(fred_raw.get('neworder')),
        },

        # ── BTC/Gold Ratio — Digital vs Physical ─────────────────────────
        'btc_gold': {
            'series':  _ts(btc_gold_ratio, n=60) if btc_gold_ratio is not None else None,
            'current': round(float(btc_gold_ratio.iloc[-1]), 4) if btc_gold_ratio is not None and len(btc_gold_ratio) >= 1 else None,
            'prev':    round(float(btc_gold_ratio.iloc[-2]), 4) if btc_gold_ratio is not None and len(btc_gold_ratio) >= 2 else None,
            'roc_4w':  _roc_4w(btc_gold_ratio),
            'ma12_series': _ts(_compute_ma(btc_gold_ratio, window=12)) if btc_gold_ratio is not None else None,
        },

        # ── BTC vs HY Spreads — Cost of Leverage Gap ─────────────────────
        'btc_vs_hy': (lambda btc=market_raw.get('BTC-USD'), hy=fred_raw.get('hy_spread'): {
            'btc_series': _ts(btc.resample('ME').last().dropna(), n=36) if btc is not None else None,
            'hy_series':  _ts(hy.resample('ME').last().dropna(), n=36) if hy is not None else None,
            'btc_current': _latest(btc) if btc is not None else None,
            'hy_current':  _latest(hy) if hy is not None else None,
        })(),

        # ── Real Yield Trap — DFII10 + 200d MA ───────────────────────────
        'real_yield_trap': (lambda ry=fred_raw.get('dfii10'): {
            'series':     _ts(ry, n=520) if ry is not None else None,
            'ma200_series': _ts(_compute_ma(ry, window=200)) if ry is not None else None,
            'current':    _latest(ry),
            'ma200':      _latest(_compute_ma(ry, window=200)) if ry is not None else None,
            'roc_4w':     _roc_4w(ry),
        })(),

        # ── Put/Call Ratio + RSI Oscillator ──────────────────────────────
        'pcr': (lambda s=pcr_series: {
            'series':     _ts(s, n=252) if s is not None else None,
            'rsi_series': _ts(_compute_rsi(s), n=252) if s is not None else None,
            'current':    _latest(s),
            'rsi_current': _latest(_compute_rsi(s)) if s is not None else None,
        })(),

        # ── SPX Options Regime ────────────────────────────────────────────
        'spx_options': spx_options,
    }

    # ── AI-generated macro summary (runs last, uses full output) ─────────
    output['macro_summary'] = _generate_macro_summary(output)

    return output


def _generate_macro_summary(data: dict) -> dict:
    """Call Claude Haiku to synthesize all dashboard signals into a War Room brief."""
    try:
        import os, anthropic
        from dotenv import load_dotenv
        load_dotenv(r'C:\QuantLab\Data_Lab\.env')
        api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise ValueError("No API key")

        # Collect key scalars for the prompt
        regime     = data.get('regime', {})
        nl         = data.get('net_liquidity', {})
        rrp        = data.get('rrp_shadow', {})
        yc         = data.get('fred_current', {})
        rates      = data.get('rates', {})
        cot_es     = data.get('cot', {}).get('ES', {})
        sloos      = data.get('sloos', {})
        mmf        = data.get('retail_mmf', {})
        sticky     = data.get('sticky_cpi', {})
        stlfsi4    = data.get('stlfsi4_current')
        cg         = data.get('copper_gold', {})
        trucks     = data.get('heavy_trucks', {})
        rco        = data.get('rate_cut_odds', {})
        market     = data.get('market', {})

        metrics = f"""
REGIME: {regime.get('regime','?')} (score {regime.get('score','?')}/10)
SPY 5d: {market.get('spy_5d','?')}%
Net Liquidity: ${nl.get('current_T','?')}T | 4wk ROC: {nl.get('roc_4w','?')}% | Regime: {nl.get('regime','?')}
RRP: ${rrp.get('current','?')}B | 4wk ROC: {rrp.get('roc_4w','?')}%
Yield Curve (10Y-2Y): {yc.get('t10y2y','?')}% | 4wk delta: {rates.get('t10y2y_roc_4w','?')}pp
10Y Real Yield: {cg.get('real_yield_current','?')}%
STLFSI4: {stlfsi4} (below 0 = green light for momentum)
COT ES: Net {cot_es.get('current','?')} contracts | Trajectory: {cot_es.get('trajectory','?')} | COT Index: {cot_es.get('cot_index','?')}/100
SLOOS (bank tightening): {sloos.get('current','?')}%
Retail MMF dry powder: ${mmf.get('current','?')}B
Sticky CPI: {sticky.get('current','?')}% YoY
Copper/Gold ratio ROC 4wk: {cg.get('ratio_roc_4w','?')}%
Heavy Trucks: {trucks.get('current','?')}K units
Rate cut odds: {str(rco.get('meeting','?'))[:60]}
"""

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            messages=[{
                'role': 'user',
                'content': (
                    f"You are a macro analyst for a prop trader. Synthesize these dashboard readings "
                    f"into a concise War Room brief. Write exactly 4 sentences: "
                    f"(1) overall regime and liquidity posture, "
                    f"(2) the biggest risk or tail risk right now, "
                    f"(3) the biggest opportunity or tailwind, "
                    f"(4) one concrete action bias for today. "
                    f"Be direct, specific, use the numbers. No preamble.\n\n{metrics}"
                )
            }]
        )
        text = resp.content[0].text.strip()
        # Split into sentences for display
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!])\s+', text) if s.strip()]
        return {
            'text': text,
            'sentences': sentences,
            'generated_at': datetime.now().strftime('%H:%M CT'),
        }

    except Exception as e:
        print(f"  ⚠ Macro summary generation failed: {e}")
        return _rule_based_macro_summary(data)


def _rule_based_macro_summary(data: dict) -> dict:
    """Fallback rule-based summary when Claude API unavailable."""
    regime   = data.get('regime', {}).get('regime', 'UNKNOWN')
    nl       = data.get('net_liquidity', {})
    rrp      = data.get('rrp_shadow', {})
    cot_es   = data.get('cot', {}).get('ES', {})
    stlfsi4  = data.get('stlfsi4_current', 0) or 0
    cg       = data.get('copper_gold', {})

    s1 = f"Regime is {regime} with net liquidity {nl.get('regime','unknown')} and {nl.get('roc_4w',0):+.1f}% 4-week ROC."
    s2 = f"RRP shock absorber at ${rrp.get('current',0):.0f}B — {'critically low, fragile tape' if (rrp.get('current') or 999) < 100 else 'some buffer remains'}."
    s3 = f"COT positioning: {cot_es.get('trajectory','unknown')} with COT Index {cot_es.get('cot_index','?')}/100. Copper/Gold {cg.get('ratio_roc_4w',0):+.1f}% 4wk."
    s4 = f"Stress regime {'ELEVATED — tighten stops' if stlfsi4 > 0 else 'LOW — green light for momentum'} (STLFSI4: {stlfsi4:.4f})."

    text = ' '.join([s1, s2, s3, s4])
    return {'text': text, 'sentences': [s1, s2, s3, s4], 'generated_at': datetime.now().strftime('%H:%M CT')}


def main():
    args = parse_args('QuantLab Macro Collector v2')
    if args.dry_run:
        print("📊 Macro Collector v2 — DRY RUN")
        print(f"  FRED series: {list(FRED_SERIES.keys())}")
        print(f"  Market tickers: {MARKET_TICKERS}")
        return
    data = collect()
    path = write_output('macro_regime', 'latest.json', data, 'macro_collector_v2')
    print(f"  ✅ Written to {path}")


if __name__ == '__main__':
    main()

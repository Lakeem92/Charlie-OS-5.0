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
    # Inflation structure
    'corestickm': 'CORESTICKM159SFRBATL',  # Sticky price CPI less shelter (% YoY)
}

SECTOR_ETFS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLC', 'XLI', 'XLB', 'XLRE', 'XLU', 'XLP', 'XLY']
MARKET_TICKERS = ['^GSPC', '^VIX', '^VIX3M', '^RUT', 'DX-Y.NYB', 'SPY'] + SECTOR_ETFS

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
        'GC': ('088691', 'M_Money_Positions_Long_ALL', 'M_Money_Positions_Short_ALL'),
        'SI': ('084691', 'M_Money_Positions_Long_ALL', 'M_Money_Positions_Short_ALL'),
        'HG': ('085692', 'M_Money_Positions_Long_ALL', 'M_Money_Positions_Short_ALL'),
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
    print(f"    Got COT for: {list(cot_raw.keys()) if cot_raw else 'none'}")

    # Derived
    print("  Computing derived series...")
    net_liq, liq_parts = _compute_net_liquidity(fred_raw)
    xly_xlp = _compute_xly_xlp(market_raw)
    sofr_iorb = _compute_sofr_iorb_spread(fred_raw)
    sector_rel = _compute_sector_relative(market_raw)

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
    }

    return output


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

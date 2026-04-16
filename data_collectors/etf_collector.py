"""
QuantLab ETF Collector v2 — Structural Squeeze Scores
Pulls price data + computes 4-signal structural squeeze scores for Tier 1 ETFs.

Squeeze Score signals:
  Signal 1: Short Interest / Days-to-Cover (yfinance proxy)
  Signal 2: Options GEX + Max Pain (yfinance option_chain)
  Signal 3: Dark Pool Off-Exchange Ratio (FINRA if available, else skip)
  Signal 4: Valuation vs reference (yfinance info)
  [Signal 5: 13F Institutional Flow — skipped, edgartools optional]

Output: catalyst_analysis_db/etf_structural/latest.json
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import pandas as pd
from datetime import datetime, timedelta
from data_collectors.collector_utils import (
    write_output, load_watchlist, safe_api_call, parse_args
)

# ── Leveraged / inverse ETF exclusion list ────────────────────────────────────
# Kept in watchlist for structural scoring but excluded from momentum leaderboard
EXCLUDE_FROM_RANKINGS = {
    # Direxion 3x/2x — US
    'SPXL', 'SPXS', 'TQQQ', 'SQQQ', 'UDOW', 'SDOW',
    'URTY', 'SRTY', 'TNA', 'TZA', 'FAS', 'FAZ',
    'ERX', 'ERY', 'NAIL', 'DRN', 'DRV', 'BULL', 'BEAR',
    'SOXL', 'SOXS', 'TECL', 'TECS', 'CURE', 'SICK',
    # Direxion 3x/2x — International
    'MEXX', 'BRZU', 'EURL', 'INDL', 'EDC', 'EDZ',
    'YINN', 'YANG', 'RORU', 'RUSL', 'RUSS',
    'CHAU', 'CHAD', 'KORU', 'DFEN', 'DUSL', 'WEBL', 'WEBS',
    'WANT', 'PILL', 'OILU', 'OILD',
    # ProShares Ultra/Short
    'UPRO', 'SPXU', 'QLD', 'QID', 'SSO', 'SDS',
    'LABU', 'LABD', 'NUGT', 'DUST', 'JNUG', 'JDST',
    # Volatility products
    'UVXY', 'SVXY', 'VIXY', 'VXX', 'TVIX',
    # Crypto leveraged/single-asset
    'BITX', 'ETHU', 'ETOR',
    # Misc leveraged
    'FNGU', 'FNGD', 'DPST', 'BNKU', 'BNKD', 'HIBL', 'HIBS',
    'MIDU', 'MIDZ', 'RWGV',
}

# ── Price + momentum data ──────────────────────────────────────────────────────

def _fetch_etf_data(tickers: list[str]) -> dict:
    """Fetch price data for ETFs via yfinance and compute momentum metrics."""
    import yfinance as yf

    raw = safe_api_call(
        yf.download, tickers,
        period='6mo', auto_adjust=True, progress=False, threads=True,
        default=None, label='yfinance ETF bulk download'
    )
    if raw is None or raw.empty:
        return {}

    close = raw['Close'] if 'Close' in raw.columns else raw
    data = {}

    now = datetime.now()
    ytd_start = datetime(now.year, 1, 1)

    for ticker in tickers:
        col = ticker
        if col not in close.columns:
            continue
        series = close[col].dropna()
        if len(series) < 2:
            continue

        last = float(series.iloc[-1])

        ret_5d = round((last / float(series.iloc[-6]) - 1) * 100, 2) if len(series) >= 6 else None
        ret_20d = round((last / float(series.iloc[-21]) - 1) * 100, 2) if len(series) >= 21 else None

        ytd_ret = None
        ytd_series = series[series.index >= pd.Timestamp(ytd_start)]
        if len(ytd_series) >= 2:
            ytd_ret = round((last / float(ytd_series.iloc[0]) - 1) * 100, 2)

        roc_5d = None
        if len(series) >= 6:
            prev = float(series.iloc[-6])
            if prev > 0:
                roc_5d = round(((last - prev) / prev) * 100, 2)

        data[ticker] = {
            'price': round(last, 2),
            'ret_5d': ret_5d,
            'ret_20d': ret_20d,
            'ytd': ytd_ret,
            'roc_5d': roc_5d,
        }

    return data


# ── Signal 1: Short Interest / Days-to-Cover ──────────────────────────────────

def _get_short_interest(ticker: str) -> dict:
    """Pull short interest signal via yfinance info (proxy for SI)."""
    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info
        short_pct_float = info.get('shortPercentOfFloat')   # e.g. 0.12 = 12%
        short_ratio = info.get('shortRatio')                 # days to cover

        signal_text = None
        signal_pts = 0

        if short_pct_float is not None:
            pct = short_pct_float * 100
            if pct > 10:
                signal_pts = 2
                signal_text = f"SI {pct:.1f}% of float — EXTREME short interest. Squeeze fuel present."
            elif pct > 5:
                signal_pts = 1
                signal_text = f"SI {pct:.1f}% of float — Elevated. Squeeze possible on catalyst."
            else:
                signal_text = f"SI {pct:.1f}% of float — Normal. No squeeze setup from SI alone."

        elif short_ratio is not None:
            if short_ratio > 5:
                signal_pts = 2
                signal_text = f"Days-to-cover {short_ratio:.1f} — EXTREME. Shorts need 5+ days to exit."
            elif short_ratio > 3:
                signal_pts = 1
                signal_text = f"Days-to-cover {short_ratio:.1f} — Elevated. Potential squeeze candidate."
            else:
                signal_text = f"Days-to-cover {short_ratio:.1f} — Normal. No structural short squeeze."

        return {
            'pts': signal_pts,
            'short_pct_float': round(short_pct_float * 100, 2) if short_pct_float else None,
            'short_ratio': round(short_ratio, 1) if short_ratio else None,
            'text': signal_text or 'Short interest data unavailable',
        }
    except Exception as e:
        return {'pts': 0, 'text': f'SI unavailable: {e}'}


# ── Signal 2: Options GEX + Max Pain ─────────────────────────────────────────

def _get_options_gex_max_pain(ticker: str, spot_price: float) -> dict:
    """Compute max pain and approximate GEX from yfinance option chain."""
    import yfinance as yf
    try:
        stock = yf.Ticker(ticker)
        expiries = stock.options
        if not expiries:
            return {'pts': 0, 'text': 'No options data'}

        # Find nearest expiry that's at least 3 days out
        today = datetime.now().date()
        valid = []
        for exp in expiries:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                if (exp_date - today).days >= 3:
                    valid.append(exp)
            except Exception:
                pass

        if not valid:
            return {'pts': 0, 'text': 'No valid expiry found'}

        nearest = valid[0]
        chain = stock.option_chain(nearest)
        calls = chain.calls[['strike', 'openInterest', 'impliedVolatility']].dropna()
        puts = chain.puts[['strike', 'openInterest', 'impliedVolatility']].dropna()

        if calls.empty or puts.empty:
            return {'pts': 0, 'text': 'Empty option chain'}

        # Max pain: minimize total value of all options at expiry
        all_strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
        # Use strikes within 25% of spot
        strikes = [s for s in all_strikes if 0.75 * spot_price <= s <= 1.25 * spot_price]
        if not strikes:
            strikes = all_strikes

        min_pain = float('inf')
        max_pain_strike = strikes[len(strikes) // 2]  # fallback: ATM

        for s in strikes:
            call_pain = float(((calls[calls['strike'] <= s]['strike'] - s).abs() * calls[calls['strike'] <= s]['openInterest']).sum())
            put_pain = float(((puts[puts['strike'] >= s]['strike'] - s).abs() * puts[puts['strike'] >= s]['openInterest']).sum())
            total = call_pain + put_pain
            if total < min_pain:
                min_pain = total
                max_pain_strike = s

        # GEX approximation: net call OI minus put OI near ATM (within 5%)
        atm_calls = calls[(calls['strike'] >= spot_price * 0.97) & (calls['strike'] <= spot_price * 1.03)]
        atm_puts = puts[(puts['strike'] >= spot_price * 0.97) & (puts['strike'] <= spot_price * 1.03)]
        net_atm_oi = float(atm_calls['openInterest'].sum()) - float(atm_puts['openInterest'].sum())
        gex_sign = 'POSITIVE' if net_atm_oi >= 0 else 'NEGATIVE'

        # Score
        mp_dist_pct = abs(max_pain_strike - spot_price) / spot_price * 100
        pts = 0
        if gex_sign == 'NEGATIVE':
            pts += 1  # negative GEX = dealers short gamma = amplified moves
        if mp_dist_pct > 5:
            pts += 1  # max pain far from spot = strong gravitational pull

        text = (
            f"Max pain ${max_pain_strike:.0f} ({mp_dist_pct:.1f}% from spot), "
            f"Expiry: {nearest}, GEX: {gex_sign} (ATM net OI: {int(net_atm_oi):+,})"
        )
        if pts >= 2:
            text += " — 🔴 HIGH squeeze amplification from options"
        elif pts == 1:
            text += " — 🟡 Moderate options pressure"

        return {
            'pts': pts,
            'max_pain': round(max_pain_strike, 2),
            'max_pain_dist_pct': round(mp_dist_pct, 2),
            'expiry': nearest,
            'gex_sign': gex_sign,
            'text': text,
        }
    except Exception as e:
        return {'pts': 0, 'text': f'Options data error: {e}'}


# ── Signal 3: Dark Pool Ratio — FINRA API ─────────────────────────────────────

def _get_dark_pool_ratio(ticker: str) -> dict:
    """
    Attempt FINRA RegSHO API for off-exchange volume.
    Falls back gracefully if unavailable.
    """
    import requests
    try:
        # FINRA API: equity short volume data (off-exchange proxy)
        url = "https://api.finra.org/data/group/otcmarket/name/regShoDaily"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "compareFilters": [
                {"compareType": "equal", "fieldName": "issueName", "fieldValue": ticker}
            ],
            "limit": 10,
            "offset": 0
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                # Calculate off-exchange ratio from short volume data
                return {
                    'pts': 0,
                    'text': f'FINRA data available — {len(data)} records',
                    'available': True,
                }
    except Exception:
        pass

    return {
        'pts': 0,
        'text': 'Dark pool ratio: FINRA API unavailable (scoring from 8 pts)',
        'available': False,
    }


# ── Signal 4: Valuation vs Reference ─────────────────────────────────────────

def _get_valuation_signal(ticker: str) -> dict:
    """Pull P/E, P/B via yfinance and compare vs rough historical baselines."""
    import yfinance as yf

    # Rough 5-year historical baselines for major ETFs (P/E)
    PE_BASELINES = {
        'SPY': 20.0, 'QQQ': 26.0, 'IWM': 18.0, 'XLF': 14.0,
        'XLE': 12.0, 'XLK': 28.0, 'XLV': 18.0, 'XLI': 18.0,
        'GDX': 15.0, 'SLV': None, 'GLD': None,
        'SMH': 22.0, 'SOXX': 22.0, 'ARKK': None,
    }

    try:
        info = yf.Ticker(ticker).info
        pe = info.get('trailingPE') or info.get('forwardPE')
        pb = info.get('priceToBook')

        pts = 0
        text_parts = []

        baseline_pe = PE_BASELINES.get(ticker)
        if pe and baseline_pe:
            discount_pct = (baseline_pe - pe) / baseline_pe * 100
            if discount_pct > 20:
                pts += 2
                text_parts.append(f"P/E {pe:.1f}x — HISTORICAL LOW ({discount_pct:.0f}% below 5yr baseline {baseline_pe}x). Smart money accumulation signal.")
            elif discount_pct > 10:
                pts += 1
                text_parts.append(f"P/E {pe:.1f}x — Below historical average ({baseline_pe}x). Attractive vs history.")
            else:
                text_parts.append(f"P/E {pe:.1f}x — Near historical average ({baseline_pe}x). Fairly valued.")
        elif pe:
            text_parts.append(f"P/E {pe:.1f}x (no baseline for comparison)")

        if pb:
            text_parts.append(f"P/B {pb:.2f}x")

        if not text_parts:
            return {'pts': 0, 'text': 'Valuation data unavailable for ETF'}

        return {
            'pts': pts,
            'pe': round(pe, 2) if pe else None,
            'pb': round(pb, 2) if pb else None,
            'text': ' | '.join(text_parts),
        }
    except Exception as e:
        return {'pts': 0, 'text': f'Valuation unavailable: {e}'}


# ── Squeeze Score Aggregator ───────────────────────────────────────────────────

def _generate_squeeze_implication(score: int, max_score: int, ticker: str, signals: dict) -> str:
    """Generate plain-English implication for the squeeze score."""
    ratio = score / max_score if max_score > 0 else 0

    if ratio >= 0.6:  # score >= 6 out of 10 (or equivalent)
        return (
            f"🔴 SQUEEZE WATCH — {ticker} structural setup scoring {score}/{max_score}. "
            f"Multiple institutional signals converging: short fuel + options amplification. "
            f"On catalyst: move could accelerate 2-3x normal. Size entries carefully — "
            f"these setups can also snap back violently."
        )
    elif ratio >= 0.35:
        return (
            f"🟡 ELEVATED — {ticker} showing {score}/{max_score} squeeze signals. "
            f"Setup building but not at full tension. Watch for incoming catalyst to activate."
        )
    else:
        return (
            f"🟢 NORMAL — {ticker} {score}/{max_score}. "
            f"No structural squeeze buildup detected. Trade on momentum only."
        )


def _compute_squeeze_score(ticker: str, spot_price: float) -> dict:
    """
    Compute 4-signal structural squeeze score for a Tier 1 ETF.
    Max score: 8 (Signal 3 dark pool skipped = -2 from theoretical max 10).
    """
    print(f"    {ticker}: computing squeeze signals...")

    # Signal 1: Short Interest
    si = safe_api_call(_get_short_interest, ticker, default={'pts': 0, 'text': 'SI unavailable'}, label=f'{ticker} SI')

    # Signal 2: Options GEX + Max Pain
    opts = safe_api_call(_get_options_gex_max_pain, ticker, spot_price, default={'pts': 0, 'text': 'Options unavailable'}, label=f'{ticker} options')

    # Signal 3: Dark Pool (attempt FINRA, usually unavailable)
    dp = safe_api_call(_get_dark_pool_ratio, ticker, default={'pts': 0, 'text': 'Dark pool unavailable', 'available': False}, label=f'{ticker} dark pool')

    # Signal 4: Valuation
    val = safe_api_call(_get_valuation_signal, ticker, default={'pts': 0, 'text': 'Valuation unavailable'}, label=f'{ticker} valuation')

    # Total score
    dp_available = dp.get('available', False)
    max_score = 8 if not dp_available else 10

    total_pts = (si.get('pts', 0) + opts.get('pts', 0) + dp.get('pts', 0) + val.get('pts', 0))
    # Cap at max
    total_pts = min(total_pts, max_score)

    # Label
    ratio = total_pts / max_score if max_score > 0 else 0
    if ratio >= 0.6:
        label = '🔴 SQUEEZE WATCH'
        css = 'squeeze-high'
    elif ratio >= 0.35:
        label = '🟡 ELEVATED'
        css = 'squeeze-mid'
    else:
        label = '🟢 NORMAL'
        css = 'squeeze-low'

    implication = _generate_squeeze_implication(total_pts, max_score, ticker, {})

    print(f"      Score: {total_pts}/{max_score} ({label})")

    return {
        'squeeze_score': total_pts,
        'squeeze_max': max_score,
        'squeeze_label': label,
        'squeeze_css': css,
        'si_pts': si.get('pts', 0),
        'si_signal': si.get('text', '—'),
        'si_short_pct': si.get('short_pct_float'),
        'si_days_cover': si.get('short_ratio'),
        'opts_pts': opts.get('pts', 0),
        'opts_signal': opts.get('text', '—'),
        'opts_max_pain': opts.get('max_pain'),
        'opts_mp_dist': opts.get('max_pain_dist_pct'),
        'opts_gex': opts.get('gex_sign'),
        'dp_pts': dp.get('pts', 0),
        'dp_signal': dp.get('text', '—'),
        'dp_available': dp_available,
        'val_pts': val.get('pts', 0),
        'val_signal': val.get('text', '—'),
        'val_pe': val.get('pe'),
        'val_pb': val.get('pb'),
        'implication': implication,
    }


# ── Table builders ─────────────────────────────────────────────────────────────

def _build_tier_tables(etf_data: dict, watchlist: pd.DataFrame, compute_squeeze: bool = True) -> tuple[list, list]:
    """Build Tier 1 and Tier 2 table rows from ETF data."""
    tier1 = []
    tier2 = []

    for _, row in watchlist.iterrows():
        ticker = row['ticker']
        tier = int(row['tier'])
        d = etf_data.get(ticker, {})
        if not d:
            continue

        entry = {
            'ticker': ticker,
            'price': d.get('price'),
            'ret_5d': d.get('ret_5d'),
            'ytd': d.get('ytd'),
            'roc_5d': d.get('roc_5d'),
        }

        if tier == 1:
            if compute_squeeze and d.get('price'):
                squeeze = _compute_squeeze_score(ticker, d['price'])
            else:
                squeeze = {
                    'squeeze_score': None, 'squeeze_max': 8, 'squeeze_label': '—',
                    'squeeze_css': '', 'si_signal': '—', 'opts_signal': '—',
                    'dp_signal': '—', 'val_signal': '—', 'implication': None,
                }
            entry.update(squeeze)
            tier1.append(entry)
        else:
            tier2.append(entry)

    tier1.sort(key=lambda x: x.get('ret_5d') or -999, reverse=True)
    tier2.sort(key=lambda x: x.get('ret_5d') or -999, reverse=True)

    return tier1, tier2


# ── KORU cross-asset signal ───────────────────────────────────────────────────

def _check_koru_signal(etf_data: dict) -> dict | None:
    """Flag when KORU (Korea ETF) moves >5% — semiconductor leading indicator."""
    koru = etf_data.get('KORU', {})
    if not koru or koru.get('ret_5d') is None:
        return None
    ret = koru['ret_5d']
    if abs(ret) > 5:
        direction = 'up' if ret > 0 else 'down'
        return {
            'triggered': True,
            'ret_5d': ret,
            'direction': direction,
            'implication': (
                f"KORU {ret:+.1f}% (5d) — Samsung/SK Hynix bid. "
                f"Leading indicator for SMH/SOXX by 3-5 days. "
                f"Memory cycle {'turning positive' if ret > 0 else 'rolling over'}. "
                f"{'Watch MU, AMAT, LRCX for follow-through.' if ret > 0 else 'Reduce MU, AMAT exposure short-term.'}"
            )
        }
    return {'triggered': False, 'ret_5d': ret}


# ── Main collect ──────────────────────────────────────────────────────────────

def collect(compute_squeeze: bool = True):
    """Main collection routine."""
    print("📈 ETF Collector v2 — starting...")

    watchlist = load_watchlist('etf_watchlist')
    tickers = watchlist['ticker'].tolist()
    # Also include KORU if not already present
    all_tickers = list(set(tickers + ['KORU']))

    print(f"  {len(tickers)} ETFs ({len(watchlist[watchlist.tier==1])} T1, {len(watchlist[watchlist.tier==2])} T2)")

    print("  Pulling yfinance price data...")
    etf_data = _fetch_etf_data(all_tickers)
    print(f"  Got data for {len(etf_data)} ETFs")

    if compute_squeeze:
        t1_tickers = watchlist[watchlist.tier == 1]['ticker'].tolist()
        print(f"\n  📊 Computing squeeze scores for {len(t1_tickers)} Tier 1 ETFs...")
    else:
        print("  ⚡ Squeeze computation skipped (--fast mode)")

    tier1, tier2 = _build_tier_tables(etf_data, watchlist, compute_squeeze=compute_squeeze)

    # KORU signal
    koru_signal = _check_koru_signal(etf_data)

    # Squeeze summary
    squeeze_alerts = [r for r in tier1 if r.get('squeeze_score') and r['squeeze_score'] >= 5]
    squeeze_watch = [r for r in tier1 if r.get('squeeze_score') and r['squeeze_score'] >= 6]

    # Momentum leaderboard — exclude leveraged/inverse ETFs
    tier2_leaderboard = [r for r in tier2 if r['ticker'] not in EXCLUDE_FROM_RANKINGS]

    output = {
        'tier1': tier1,
        'tier2': tier2,
        'tier2_leaderboard': tier2_leaderboard,
        'koru_signal': koru_signal,
        'squeeze_summary': {
            'watch_count': len(squeeze_watch),
            'elevated_count': len(squeeze_alerts),
            'watch_tickers': [r['ticker'] for r in squeeze_watch],
        },
        'counts': {
            'tier1_total': len(watchlist[watchlist.tier == 1]),
            'tier2_total': len(watchlist[watchlist.tier == 2]),
            'tier1_data': len(tier1),
            'tier2_data': len(tier2),
            'leaderboard_total': len(tier2_leaderboard),
        },
    }

    return output


def main():
    import argparse
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    parser = argparse.ArgumentParser(description='QuantLab ETF Collector v2')
    parser.add_argument('--dry-run', action='store_true', help='Print config and exit')
    parser.add_argument('--fast', action='store_true', help='Skip squeeze computation (price data only)')
    args = parser.parse_args()

    if args.dry_run:
        print("📈 ETF Collector v2 — DRY RUN")
        watchlist = load_watchlist('etf_watchlist')
        print(f"  Watchlist: {len(watchlist)} ETFs")
        print(f"  Tier 1: {len(watchlist[watchlist.tier==1])} (squeeze scores computed)")
        print(f"  Tier 2: {len(watchlist[watchlist.tier==2])} (price + momentum only)")
        print(f"  Squeeze signals: SI, Options GEX/MaxPain, Dark Pool (FINRA), Valuation")
        print(f"  Output: catalyst_analysis_db/etf_structural/latest.json")
        return

    compute_squeeze = not args.fast
    data = collect(compute_squeeze=compute_squeeze)

    if data.get('squeeze_summary', {}).get('watch_count', 0) > 0:
        print(f"\n  🔴 SQUEEZE WATCH: {', '.join(data['squeeze_summary']['watch_tickers'])}")

    path = write_output('etf_structural', 'latest.json', data, 'etf_collector_v2')
    print(f"\n  ✅ Written to {path}")


if __name__ == '__main__':
    main()

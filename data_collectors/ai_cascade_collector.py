"""
QuantLab AI Cascade Collector v2
Tracks the 4-flow AI supercycle convergence meter.
Adds pytrends search interest ROC for 15 supply chain search terms.
Generates implications per flow.
Output: catalyst_analysis_db/daily_briefing/ai_cascade.json
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from data_collectors.collector_utils import write_output, parse_args, safe_api_call, load_config

DATA_LAB = Path(r'C:\QuantLab\Data_Lab')
CATALYST_DB = DATA_LAB / 'catalyst_analysis_db'
PYTRENDS_CACHE = CATALYST_DB / 'daily_briefing' / 'pytrends_cache.json'

# ── 4-Flow Definitions ────────────────────────────────────────────────────────
FLOWS = {
    'silicon': {
        'label': 'SILICON',
        'emoji': '🔬',
        'tickers': ['NVDA', 'AMD', 'AVGO', 'TSM', 'INTC', 'MRVL'],
        'description': 'GPU / chip demand & supply',
    },
    'optical': {
        'label': 'OPTICAL',
        'emoji': '🔌',
        'tickers': ['ALAB', 'COHR', 'LITE', 'CIEN', 'CRDO'],
        'description': 'Optical networking / interconnect',
    },
    'power': {
        'label': 'POWER',
        'emoji': '⚡',
        'tickers': ['VST', 'CEG', 'NRG', 'EQIX', 'DLR'],
        'description': 'Data center power & infrastructure',
    },
    'demand': {
        'label': 'DEMAND',
        'emoji': '🧠',
        'tickers': ['MSFT', 'GOOGL', 'AMZN', 'META', 'CRM'],
        'description': 'Hyperscaler capex & AI adoption',
    },
}

INSTITUTIONAL_PICKS = [
    {'ticker': 'ECG',  'name': 'DC substation wiring'},
    {'ticker': 'STRL', 'name': 'DC site prep'},
    {'ticker': 'FLS',  'name': 'CDU pumps/valves'},
    {'ticker': 'HUT',  'name': 'AI power arbitrage'},
    {'ticker': 'SYM',  'name': 'AI robotics'},
]

# ── Flow classification ───────────────────────────────────────────────────────

def _classify_flow(avg_ret_5d: float) -> tuple:
    """Classify flow status and score based on average 5d return."""
    if avg_ret_5d > 2.0:
        return 'active', 100
    elif avg_ret_5d > 0.5:
        return 'active', 75
    elif avg_ret_5d > -0.5:
        return 'friction', 50
    elif avg_ret_5d > -2.0:
        return 'friction', 25
    else:
        return 'inactive', 10


def _generate_convergence_implication(flows: dict, convergence: int) -> str:
    """Generate a 1-sentence Claude-powered top-level AI cycle implication."""
    try:
        import os, anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise ValueError("No API key")
        client = anthropic.Anthropic(api_key=api_key)
        flow_summary = {k: {'status': v.get('status'), 'avg_ret_5d': v.get('avg_ret_5d')} for k, v in flows.items()}
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=120,
            messages=[{
                'role': 'user',
                'content': (
                    f"AI Supercycle: {convergence}/4 flows active. "
                    f"Flow data: {flow_summary}. "
                    "In exactly ONE sentence (max 25 words), state the trading implication for today. "
                    "Focus on what to do with AI infrastructure names. "
                    "No preamble, just the implication sentence."
                )
            }]
        )
        return resp.content[0].text.strip().rstrip('.')
    except Exception:
        # Fallback rule-based implication
        if convergence == 4:
            return 'All flows firing — maximum AI cycle conviction, size up across the supply chain'
        elif convergence >= 3:
            return 'Three flows active — strong momentum, rotate into the strongest performers'
        elif convergence >= 2:
            return 'Mixed signals — focus on the active flows, reduce exposure to laggards'
        else:
            return 'AI cycle momentum stalling — hold existing positions, no new entries'


def _generate_flow_implication(flow_key: str, flow_cfg: dict, status: str, avg_ret: float) -> str:
    """Generate Implications Doctrine text for each flow."""
    label = flow_cfg['label']
    desc = flow_cfg['description']

    if status == 'active' and avg_ret > 3:
        if flow_key == 'silicon':
            return (
                f"SILICON FLOW HOT (+{avg_ret:.1f}% avg 5d). GPU demand accelerating — "
                f"NVDA/AVGO lead. Fab orders building. "
                f"→ TRICKLE DOWN: Optical interconnect (ALAB, LITE) follows 1-3 weeks. "
                f"CDU/cooling demand (VRT, FLS) next wave. Memory (MU) repricing."
            )
        elif flow_key == 'optical':
            return (
                f"OPTICAL FLOW ACTIVE (+{avg_ret:.1f}% avg 5d). Hyperscaler scale-out driving "
                f"400G/800G interconnect orders. ALAB/COHR/LITE bid. "
                f"→ TRICKLE DOWN: Spine switches (ANET, CSCO) next. "
                f"Data center real estate (EQIX, DLR) demand confirmed."
            )
        elif flow_key == 'power':
            return (
                f"POWER FLOW ACTIVE (+{avg_ret:.1f}% avg 5d). Data center energy demand surging. "
                f"VST/CEG/NRG pricing power expanding. "
                f"→ TRICKLE DOWN: Transformer lead times extending (ETN, PWR). "
                f"Nuclear power assets (CEG) getting structural re-rating. "
                f"Small modular reactors (SMR) narrative strengthening."
            )
        elif flow_key == 'demand':
            return (
                f"DEMAND FLOW ACTIVE (+{avg_ret:.1f}% avg 5d). Hyperscalers buying — "
                f"MSFT/GOOGL/AMZN/META capex guidance elevated. "
                f"→ TRICKLE DOWN: GPU orders accelerate → Silicon flow leads next. "
                f"Enterprise AI adoption driving CRM, SNOW, DATA outperformance."
            )
    elif status == 'active':
        return (
            f"{label} flow positive (+{avg_ret:.1f}% avg 5d). Trend intact. "
            f"Monitor for acceleration signal — look for individual ticker breakouts within the flow."
        )
    elif status == 'friction':
        return (
            f"{label} flow in friction zone ({avg_ret:+.1f}% avg 5d). Mixed signals — "
            f"some names holding, others fading. Selective setups only. "
            f"Not enough breadth for conviction on the full flow."
        )
    else:
        return (
            f"{label} flow INACTIVE ({avg_ret:+.1f}% avg 5d). AI trade cooling in this layer. "
            f"Defensive posture. Wait for re-ignition — watch for institutional flow returning via 13F or block prints."
        )


# ── Price data ────────────────────────────────────────────────────────────────

def _fetch_price_data(all_tickers: list) -> dict:
    """Bulk download via yfinance."""
    import yfinance as yf
    raw = safe_api_call(
        yf.download, all_tickers,
        period='1mo', group_by='ticker', progress=False,
        default=None, label='yfinance AI cascade'
    )
    return raw


def _extract_ticker_data(raw, ticker: str, all_tickers: list) -> dict | None:
    """Extract price data for one ticker from bulk download."""
    try:
        if raw is None:
            return None
        df = raw[ticker] if len(all_tickers) > 1 else raw
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.droplevel(1) if df.columns.nlevels > 1 else df.columns
        df = df.dropna(subset=['Close'])
        if df.empty or len(df) < 2:
            return None

        price = float(df['Close'].iloc[-1])
        ret_5d = ((price - float(df['Close'].iloc[-6])) / float(df['Close'].iloc[-6])) * 100 if len(df) >= 6 else None
        ret_1d = ((price - float(df['Close'].iloc[-2])) / float(df['Close'].iloc[-2])) * 100

        return {
            'price': round(price, 2),
            'ret_5d': round(ret_5d, 2) if ret_5d is not None else None,
            'ret_1d': round(ret_1d, 2),
        }
    except Exception:
        return None


# ── pytrends engine ───────────────────────────────────────────────────────────

def _load_pytrends_cache() -> dict:
    """Load cached pytrends data."""
    if PYTRENDS_CACHE.exists():
        try:
            return json.loads(PYTRENDS_CACHE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def _save_pytrends_cache(data: dict):
    """Save pytrends data to cache."""
    PYTRENDS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    PYTRENDS_CACHE.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')


def _fetch_pytrends_data(queries: list) -> dict:
    """
    Pull Google Trends interest_over_time for each search term.
    Computes 4-week and 12-week ROC.
    Falls back to cache if rate limited.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("  ⚠ pytrends not installed — using cache only")
        return _load_pytrends_cache()

    cache = _load_pytrends_cache()
    results = {}
    rate_limited = False

    import random

    for i, q in enumerate(queries):
        term = q['term']
        if rate_limited:
            # Use cache for remaining terms
            if term in cache:
                results[term] = cache[term]
            continue

        try:
            print(f"    [{i+1}/{len(queries)}] pytrends: {term[:40]}...")
            # Fresh TrendReq per query — reduces 429 risk vs reusing a session
            delay = random.uniform(8, 14) if i > 0 else random.uniform(2, 4)
            time.sleep(delay)
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2, backoff_factor=2.0)
            pytrends.build_payload([term], timeframe='today 3-m', geo='')
            df = pytrends.interest_over_time()

            if df is None or df.empty or term not in df.columns:
                if term in cache:
                    results[term] = cache[term]
                continue

            vals = df[term].tolist()
            dates = [str(d.date()) for d in df.index]

            # 4-week ROC (last 4 weeks vs prior 4 weeks)
            roc_4w = None
            if len(vals) >= 8:
                recent_4w = sum(vals[-4:]) / 4
                prior_4w = sum(vals[-8:-4]) / 4
                if prior_4w > 0:
                    roc_4w = round((recent_4w / prior_4w - 1) * 100, 1)

            # 12-week ROC
            roc_12w = None
            if len(vals) >= 24:
                recent_4w = sum(vals[-4:]) / 4
                prior_12w = sum(vals[-24:-12]) / 4
                if prior_12w > 0:
                    roc_12w = round((recent_4w / prior_12w - 1) * 100, 1)

            latest = vals[-1] if vals else None
            trend = 'RISING' if (roc_4w is not None and roc_4w > 20) else \
                    'FALLING' if (roc_4w is not None and roc_4w < -20) else 'FLAT'

            results[term] = {
                'dates': dates[-13:],   # last 13 weeks
                'values': vals[-13:],
                'roc_4w': roc_4w,
                'roc_12w': roc_12w,
                'latest': latest,
                'trend': trend,
                'flow': q.get('flow'),
                'layer': q.get('layer'),
                'tickers': q.get('tickers', []),
                'lead_time': q.get('lead_time'),
                'fetched_at': datetime.now().isoformat(),
            }

        except Exception as e:
            err_str = str(e).lower()
            if '429' in err_str or 'rate' in err_str or 'too many' in err_str:
                print(f"  ⚠ pytrends rate limited at query {i+1} — using cache for remainder")
                rate_limited = True
                if term in cache:
                    results[term] = cache[term]
            else:
                print(f"  ⚠ pytrends error for '{term}': {e}")
                if term in cache:
                    results[term] = cache[term]

    # Merge with cache for any missing
    for q in queries:
        term = q['term']
        if term not in results and term in cache:
            results[term] = cache[term]

    # Save updated cache
    merged = {**cache, **results}
    _save_pytrends_cache(merged)

    if rate_limited:
        print("  ⚠️ pytrends rate limited — data from cache where available")

    return results


def _summarize_pytrends(pytrends_data: dict, queries: list) -> dict:
    """Build per-flow pytrends summary."""
    flow_trends = {'silicon': [], 'optical': [], 'power': [], 'demand': []}

    for q in queries:
        term = q['term']
        flow = q.get('flow', '').lower()
        if term in pytrends_data and flow in flow_trends:
            d = pytrends_data[term]
            flow_trends[flow].append({
                'term': term,
                'layer': q.get('layer'),
                'roc_4w': d.get('roc_4w'),
                'roc_12w': d.get('roc_12w'),
                'trend': d.get('trend', 'FLAT'),
                'tickers': q.get('tickers', []),
                'lead_time': q.get('lead_time'),
            })

    # Summarize per flow (capitalize for display)
    summaries = {}
    for flow, terms in flow_trends.items():
        flow = flow.capitalize()  # silicon → Silicon for display
        if not terms:
            continue
        active = [t for t in terms if t['trend'] == 'RISING']
        falling = [t for t in terms if t['trend'] == 'FALLING']
        avg_roc = None
        rocs = [t['roc_4w'] for t in terms if t['roc_4w'] is not None]
        if rocs:
            avg_roc = round(sum(rocs) / len(rocs), 1)

        summaries[flow] = {
            'terms': terms,
            'rising_count': len(active),
            'falling_count': len(falling),
            'avg_roc_4w': avg_roc,
            'flow_trend': 'RISING' if avg_roc and avg_roc > 10 else 'FALLING' if avg_roc and avg_roc < -10 else 'FLAT',
        }

    return summaries


# ── Main collect ──────────────────────────────────────────────────────────────

def collect(fetch_pytrends: bool = True):
    """Main collection routine."""
    print("🧠 AI Cascade Collector v2 — starting...")

    # Load pytrends config
    try:
        queries = load_config('pytrends_queries')
        print(f"  Loaded {len(queries)} pytrends search terms")
    except Exception as e:
        print(f"  ⚠ Could not load pytrends_queries.json: {e}")
        queries = []

    # Fetch price data
    all_tickers = sorted(set(
        t for flow in FLOWS.values() for t in flow['tickers']
    ) | set(p['ticker'] for p in INSTITUTIONAL_PICKS))

    print(f"  Downloading {len(all_tickers)} tickers...")
    import yfinance as yf
    raw = safe_api_call(
        yf.download, all_tickers,
        period='1mo', group_by='ticker', progress=False,
        default=None, label='yfinance AI cascade'
    )

    # Process flows
    flows = {}
    active_count = 0

    for flow_key, flow_cfg in FLOWS.items():
        tickers_data = []
        returns_5d = []

        for ticker in flow_cfg['tickers']:
            td = _extract_ticker_data(raw, ticker, all_tickers)
            if td is None:
                continue
            tickers_data.append({'ticker': ticker, **td})
            if td.get('ret_5d') is not None:
                returns_5d.append(td['ret_5d'])

        avg_ret = sum(returns_5d) / len(returns_5d) if returns_5d else 0
        status, score = _classify_flow(avg_ret)
        if status == 'active':
            active_count += 1

        implication = _generate_flow_implication(flow_key, flow_cfg, status, avg_ret)

        flows[flow_key] = {
            'label': flow_cfg['label'],
            'emoji': flow_cfg['emoji'],
            'description': flow_cfg['description'],
            'status': status,
            'score': score,
            'avg_ret_5d': round(avg_ret, 2),
            'tickers': tickers_data,
            'implication': implication,
        }

        emoji_map = {'active': '🟢', 'friction': '🟡', 'inactive': '🔴'}
        print(f"  {flow_cfg['emoji']} {flow_cfg['label']}: {emoji_map[status]} {status.upper()} ({avg_ret:+.2f}%)")

    # Institutional picks
    picks = []
    for pick in INSTITUTIONAL_PICKS:
        td = _extract_ticker_data(raw, pick['ticker'], all_tickers)
        if td is None:
            continue
        picks.append({
            'ticker': pick['ticker'],
            'name': pick['name'],
            **td,
        })

    # pytrends
    pytrends_data = {}
    pytrends_summary = {}
    if fetch_pytrends and queries:
        print(f"\n  📈 Fetching Google Trends for {len(queries)} search terms...")
        pytrends_data = _fetch_pytrends_data(queries)
        pytrends_summary = _summarize_pytrends(pytrends_data, queries)
        print(f"  Got trends data for {len(pytrends_data)}/{len(queries)} terms")
    else:
        # Use cache
        cache = _load_pytrends_cache()
        if cache:
            pytrends_data = cache
            pytrends_summary = _summarize_pytrends(cache, queries)
            print(f"  📈 Using cached pytrends data ({len(cache)} terms)")

    print(f"\n  🎯 CONVERGENCE: {active_count}/4 FLOWS ACTIVE")

    # Claude-powered top-level convergence implication (once per run, ~80 tokens)
    flow_implication = _generate_convergence_implication(flows, active_count)

    return {
        'flows': flows,
        'convergence': active_count,
        'flow_implication': flow_implication,
        'picks': picks,
        'pytrends': pytrends_data,
        'pytrends_summary': pytrends_summary,
        'pytrends_queries': queries,
        'pytrends_cached': not fetch_pytrends,
        'counts': {'flows': len(flows), 'picks': len(picks), 'trends': len(pytrends_data)},
    }


def main():
    import argparse
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    parser = argparse.ArgumentParser(description='QuantLab AI Cascade Collector v2')
    parser.add_argument('--dry-run', action='store_true', help='Print config and exit')
    parser.add_argument('--no-trends', action='store_true', help='Skip pytrends (use cache only)')
    args = parser.parse_args()

    if args.dry_run:
        print("🧠 AI Cascade Collector v2 — DRY RUN")
        print(f"  Flows: {list(FLOWS.keys())}")
        print(f"  Institutional picks: {[p['ticker'] for p in INSTITUTIONAL_PICKS]}")
        try:
            qs = load_config('pytrends_queries')
            print(f"  pytrends search terms: {len(qs)}")
        except Exception:
            print("  pytrends_queries.json: not loaded")
        return

    fetch_trends = not args.no_trends
    data = collect(fetch_pytrends=fetch_trends)
    path = write_output('daily_briefing', 'ai_cascade.json', data, 'ai_cascade_collector_v2')
    print(f"  ✅ Written to {path}")


if __name__ == '__main__':
    main()

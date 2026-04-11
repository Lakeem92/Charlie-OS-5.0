import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

# Force UTF-8 on Windows terminals (prevents emoji encoding errors)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

"""
QuantLab Watchlist News Scanner
War Room pre-market feed — ticker news + sector catalyst sweeps
Writes/appends to News_flow/YYYY-MM-DD.md
Generates/overwrites News_flow/YYYY-MM-DD.html (all runs, newest first)
"""

import json
import time
import requests
import difflib
import html as html_module
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(r'C:\QuantLab\Data_Lab')
NEWS_FLOW    = ROOT / 'News_flow'
MCP_JSON     = ROOT / '.vscode' / 'mcp.json'
NEWS_FLOW.mkdir(parents=True, exist_ok=True)

CT = ZoneInfo('America/Chicago')


# ── Key loading ────────────────────────────────────────────────────────────────
def _load_env():
    """Try dotenv at project root, then shared/config keys."""
    env_path = ROOT / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)
        except ImportError:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip().strip('"\'')
                if k and k not in os.environ:
                    os.environ[k] = v


def _get_alpaca_keys() -> tuple:
    """Load Alpaca API key + secret from shared/config/keys/live.env."""
    try:
        from shared.config.env_loader import load_keys
        load_keys('live', override=True)
    except Exception:
        key_file = Path(r'C:\QuantLab\Data_Lab\shared\config\keys\live.env')
        if key_file.exists():
            for line in key_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    key    = os.getenv('ALPACA_API_KEY', '')
    secret = os.getenv('ALPACA_API_SECRET', '')
    return key, secret


def _get_tavily_key() -> str:
    _load_env()
    key = os.getenv('TAVILY_API_KEY', '')
    if key:
        return key
    if MCP_JSON.exists():
        try:
            cfg = json.loads(MCP_JSON.read_text())
            key = cfg.get('servers', {}).get('tavily', {}).get('env', {}).get('TAVILY_API_KEY', '')
            if key:
                return key
        except Exception:
            pass
    return ''


# ── CT timestamp helpers ───────────────────────────────────────────────────────
def _to_ct(dt_str: str) -> str:
    if not dt_str:
        return 'N/A'
    try:
        dt_str_clean = dt_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_str_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ct = dt.astimezone(CT)
        return ct.strftime('%Y-%m-%d %I:%M %p CT')
    except Exception:
        return dt_str[:16]


def _now_ct() -> datetime:
    return datetime.now(CT)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — ALPACA NEWS: TICKER-SPECIFIC NEWS
# ─────────────────────────────────────────────────────────────────────────────
def fetch_tiingo_news() -> list:
    """
    Pulls last 24h news from Alpaca News API for the full watchlist.
    Endpoint: GET https://data.alpaca.markets/v1beta1/news
    Batches in groups of 50 (Alpaca symbols param limit).
    Returns list of dicts with same keys the Tiingo section used.
    """
    api_key, api_secret = _get_alpaca_keys()
    if not api_key or not api_secret:
        print('WARNING: ALPACA_API_KEY/SECRET not found — skipping ticker news pull')
        print('   Keys should be in shared/config/keys/live.env')
        return []

    headers = {
        'APCA-API-KEY-ID':     api_key,
        'APCA-API-SECRET-KEY': api_secret,
    }

    from shared.watchlist import get_watchlist
    tickers = get_watchlist()

    start_dt = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    batch_size = 50
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]

    all_items = []
    for idx, batch in enumerate(batches):
        params = {
            'symbols':    ','.join(batch),
            'start':      start_dt,
            'limit':      50,
            'sort':       'desc',
            'include_content': 'false',
        }
        try:
            r = requests.get(
                'https://data.alpaca.markets/v1beta1/news',
                headers=headers,
                params=params,
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                for item in data.get('news', []):
                    all_items.append({
                        'ticker':       ', '.join(item.get('symbols', ['N/A'])),
                        'headline':     item.get('headline', ''),
                        'source':       item.get('source', ''),
                        'published_at': item.get('created_at', ''),
                        'url':          item.get('url', ''),
                    })
            else:
                print(f'  [WARN] Alpaca News batch {idx+1}/{len(batches)} → HTTP {r.status_code}: {r.text[:120]}')
        except Exception as e:
            print(f'  [WARN] Alpaca News batch {idx+1}/{len(batches)} failed: {e}')

        if idx < len(batches) - 1:
            time.sleep(0.2)

    def _sort_key(x):
        try:
            return datetime.fromisoformat(x['published_at'].replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    all_items.sort(key=_sort_key, reverse=True)
    return all_items


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — TAVILY: SECTOR CATALYST SWEEPS
# ─────────────────────────────────────────────────────────────────────────────

TAVILY_QUERIES = {
    'AI_DISPLACEMENT': [
        "new AI model announced OpenAI Anthropic Google Meta today",
        "AI tool replacing software jobs sector impact today",
    ],
    'REGULATORY': [
        "FDA approval rejection drug decision today",
        "FTC DOJ antitrust investigation announcement today",
        "tariff trade policy executive order stocks today",
        "defense budget contract award today",
    ],
    'MACRO_DATA': [
        "CPI PPI PCE inflation data release today",
        "jobs report NFP ADP employment data today",
        "ISM PMI manufacturing services data today",
        "retail sales housing starts economic data today",
    ],
    'COMMODITY_ENERGY': [
        "crude oil price move OPEC supply shock today",
        "copper gold lithium uranium price move today",
    ],
    'GEOPOLITICAL': [
        "Taiwan China semiconductor trade restriction today",
        "Middle East supply chain disruption today",
        "sanctions trade deal geopolitical market impact today",
    ],
    'BELLWETHER_SIGNALS': [
        "NVDA AMD TSM ASML earnings guidance update today",
        "JPM GS BAC WMT HD TGT earnings guidance today",
        "sector bellwether earnings surprise guidance cut today",
    ],
    'NON_EARNINGS_RECURRING': [
        "TSMC monthly revenue report 2026",
        "Samsung preliminary earnings results 2026",
        "Korea semiconductor exports 2026",
        "SEMI book-to-bill ratio 2026",
        "Taiwan export orders technology 2026",
    ],
}

SECTION_LABELS = {
    'AI_DISPLACEMENT':        '🤖 AI DISPLACEMENT',
    'REGULATORY':             '⚖️ REGULATORY',
    'MACRO_DATA':             '📊 MACRO DATA',
    'COMMODITY_ENERGY':       '🛢️ COMMODITY / ENERGY',
    'GEOPOLITICAL':           '🌍 GEOPOLITICAL',
    'BELLWETHER_SIGNALS':     '🏛️ BELLWETHER SIGNALS',
    'NON_EARNINGS_RECURRING': '📅 NON-EARNINGS RECURRING DATA',
}

# Color accents per section for the HTML dashboard
SECTION_COLORS = {
    'AI_DISPLACEMENT':        '#7c3aed',
    'REGULATORY':             '#dc2626',
    'MACRO_DATA':             '#2563eb',
    'COMMODITY_ENERGY':       '#d97706',
    'GEOPOLITICAL':           '#059669',
    'BELLWETHER_SIGNALS':     '#db2777',
    'NON_EARNINGS_RECURRING': '#0891b2',
}


def fetch_tavily_news() -> dict:
    tavily_key = _get_tavily_key()
    if not tavily_key:
        print('WARNING: TAVILY_API_KEY not found — skipping Tavily pull')
        return {k: [] for k in TAVILY_QUERIES}

    results = {k: [] for k in TAVILY_QUERIES}

    for pattern, queries in TAVILY_QUERIES.items():
        for query in queries:
            try:
                r = requests.post(
                    'https://api.tavily.com/search',
                    json={
                        'api_key':      tavily_key,
                        'query':        query,
                        'search_depth': 'basic',
                        'max_results':  5,
                    },
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get('results', []):
                        results[pattern].append({
                            'headline':     item.get('title', ''),
                            'source':       item.get('source') or item.get('url', '').split('/')[2] if item.get('url') else '',
                            'published_at': item.get('published_date', ''),
                            'url':          item.get('url', ''),
                            'query':        query,
                        })
                else:
                    print(f'  [WARN] Tavily [{pattern}] "{query[:40]}..." → HTTP {r.status_code}')
            except Exception as e:
                print(f'  [WARN] Tavily [{pattern}] "{query[:40]}..." failed: {e}')

            time.sleep(0.2)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────
def _parse_dt(dt_str: str) -> datetime:
    if not dt_str:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def deduplicate(items: list) -> tuple:
    seen_urls = {}
    seen_headlines = []
    dropped = 0
    result = []

    for item in items:
        url      = item.get('url', '').strip()
        headline = item.get('headline', '').strip()

        if url and url in seen_urls:
            existing = seen_urls[url]
            if _parse_dt(item['published_at']) < _parse_dt(existing['published_at']):
                result.remove(existing)
                seen_urls[url] = item
                result.append(item)
            dropped += 1
            continue

        is_dup = False
        for prev_headline, prev_item in seen_headlines:
            ratio = difflib.SequenceMatcher(None, headline.lower(), prev_headline.lower()).ratio()
            if ratio > 0.85:
                if _parse_dt(item['published_at']) < _parse_dt(prev_item['published_at']):
                    result.remove(prev_item)
                    seen_headlines.remove((prev_headline, prev_item))
                    seen_headlines.append((headline, item))
                    if prev_item.get('url'):
                        seen_urls.pop(prev_item['url'], None)
                    if url:
                        seen_urls[url] = item
                    result.append(item)
                dropped += 1
                is_dup = True
                break

        if not is_dup:
            if url:
                seen_urls[url] = item
            seen_headlines.append((headline, item))
            result.append(item)

    return result, dropped


def deduplicate_tiingo(items: list) -> tuple:
    return deduplicate(items)


def deduplicate_tavily(tavily_by_pattern: dict) -> tuple:
    flat = []
    for pattern, items in tavily_by_pattern.items():
        for item in items:
            item['_pattern'] = pattern
            flat.append(item)

    deduped_flat, dropped = deduplicate(flat)

    result = {k: [] for k in TAVILY_QUERIES}
    for item in deduped_flat:
        pattern = item.pop('_pattern', 'AI_DISPLACEMENT')
        result[pattern].append(item)

    return result, dropped


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4a — JSON SIDECAR (accumulates all runs for the day)
# ─────────────────────────────────────────────────────────────────────────────
def load_day_cache(cache_path: Path) -> list:
    """Load existing scan runs from today's JSON sidecar. Returns list of runs."""
    if not cache_path.exists():
        return []
    try:
        return json.loads(cache_path.read_text(encoding='utf-8'))
    except Exception:
        return []


def save_run_to_cache(
    cache_path: Path,
    alpaca_items: list,
    tavily_by_pattern: dict,
    dups_dropped: int,
):
    """Append current run's data to today's JSON sidecar."""
    now_ct = _now_ct()
    run = {
        'run_ts':       now_ct.isoformat(),
        'run_label':    now_ct.strftime('%I:%M %p CT').lstrip('0'),
        'alpaca_count': len(alpaca_items),
        'tavily_count': sum(len(v) for v in tavily_by_pattern.values()),
        'dups_dropped': dups_dropped,
        'alpaca_items': alpaca_items,
        'tavily':       tavily_by_pattern,
    }
    existing = load_day_cache(cache_path)
    existing.append(run)
    cache_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
    return existing  # return all runs for the day (used by HTML builder)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4b — WRITE TO News_flow/YYYY-MM-DD.md
# ─────────────────────────────────────────────────────────────────────────────
def write_markdown(
    tiingo_items: list,
    tavily_by_pattern: dict,
    tiingo_raw_count: int,
    tavily_raw_count: int,
    dups_dropped: int,
    output_path: Path,
):
    now_ct = _now_ct()
    date_str  = now_ct.strftime(f'%A %B {now_ct.day}, %Y')
    time_str  = now_ct.strftime('%I:%M %p CT')
    total     = len(tiingo_items) + sum(len(v) for v in tavily_by_pattern.values())

    lines = []
    lines.append('')
    lines.append('---')
    lines.append(f'## SCAN RUN — {date_str} {time_str}')
    lines.append(f'Alpaca News: {len(tiingo_items)} items | Tavily: {sum(len(v) for v in tavily_by_pattern.values())} items | After dedup: {total} total')
    lines.append('---')
    lines.append('')

    lines.append('### ALPACA NEWS — WATCHLIST TICKER NEWS')
    lines.append('*Ticker-specific developments from your 240-name watchlist*')
    lines.append('')

    if tiingo_items:
        for item in tiingo_items:
            ct_str = _to_ct(item['published_at'])
            lines.append(f"**{item['ticker']}** | {item['source']} | {ct_str}")
            lines.append(item['headline'])
            lines.append(f"🔗 {item['url']}")
            lines.append('')
        lines.append('*(newest first)*')
    else:
        lines.append('*No Alpaca News results — check API keys in shared/config/keys/live.env*')

    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('### TAVILY — SECTOR CATALYST SWEEPS')
    lines.append('')

    for pattern, label in SECTION_LABELS.items():
        items = tavily_by_pattern.get(pattern, [])
        lines.append(f'#### {label}')
        if pattern == 'NON_EARNINGS_RECURRING':
            lines.append('*(TSMC monthly, Samsung prelim, Korea semi exports, SEMI B2B)*')
        if items:
            for item in items:
                ct_str = _to_ct(item['published_at']) if item.get('published_at') else 'N/A'
                lines.append(f"**{item['source']}** | {ct_str}")
                lines.append(item['headline'])
                lines.append(f"🔗 {item['url']}")
                lines.append('')
        else:
            lines.append('*No results for this section*')
            lines.append('')

    lines.append('---')
    lines.append(f'*Scan complete | {dups_dropped} duplicates dropped | Runs today: 6:30 AM / 7:30 AM / 8:06 AM CT*')
    lines.append('')

    with open(output_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4c — HTML DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def _h(text: str) -> str:
    """HTML-escape a string."""
    return html_module.escape(str(text or ''))


def _build_alpaca_section(items: list) -> str:
    if not items:
        return '<p class="empty">No Alpaca News results this run — check API keys in shared/config/keys/live.env</p>'
    rows = []
    for item in items:
        ct_str = _to_ct(item.get('published_at', ''))
        url    = item.get('url', '#')
        rows.append(f'''
          <tr>
            <td class="ticker-cell">{_h(item.get("ticker",""))}</td>
            <td><a href="{_h(url)}" target="_blank" rel="noopener">{_h(item.get("headline",""))}</a></td>
            <td class="meta-cell">{_h(item.get("source",""))}</td>
            <td class="meta-cell">{_h(ct_str)}</td>
          </tr>''')
    return f'''
      <table class="news-table">
        <thead><tr><th>Ticker</th><th>Headline</th><th>Source</th><th>Time (CT)</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>'''


def _build_tavily_section(pattern: str, items: list) -> str:
    label = SECTION_LABELS.get(pattern, pattern)
    color = SECTION_COLORS.get(pattern, '#42a5f5')
    if not items:
        content = '<p class="empty">No results</p>'
    else:
        cards = []
        for item in items:
            ct_str = _to_ct(item.get('published_at', ''))
            url    = item.get('url', '#')
            cards.append(f'''
            <div class="article-row">
              <a href="{_h(url)}" target="_blank" rel="noopener" class="article-headline">{_h(item.get("headline",""))}</a>
              <span class="article-meta">{_h(item.get("source",""))} &nbsp;·&nbsp; {_h(ct_str)}</span>
            </div>''')
        content = ''.join(cards)
    return f'''
      <div class="cat-block">
        <div class="cat-label" style="border-left:3px solid {color};padding-left:8px;color:{color};">{_h(label)}</div>
        {content}
      </div>'''


def _build_run_card(run: dict, idx: int, total_runs: int) -> str:
    """Build one collapsible scan-run card. idx=0 is newest."""
    label      = run.get('run_label', 'Unknown')
    ts         = run.get('run_ts', '')
    a_count    = run.get('alpaca_count', 0)
    t_count    = run.get('tavily_count', 0)
    dups       = run.get('dups_dropped', 0)
    alpaca     = run.get('alpaca_items', [])
    tavily     = run.get('tavily', {})

    is_latest  = (idx == total_runs - 1)
    open_attr  = 'open' if is_latest else ''
    badge      = '<span class="badge-latest">LATEST</span>' if is_latest else ''

    # Build Tavily sections
    tavily_html = ''
    for pattern in TAVILY_QUERIES:
        tavily_html += _build_tavily_section(pattern, tavily.get(pattern, []))

    return f'''
    <details class="run-card" {open_attr}>
      <summary class="run-summary">
        <span class="run-time">{_h(label)}</span>
        {badge}
        <span class="run-stats">{a_count} ticker items &nbsp;·&nbsp; {t_count} sector items &nbsp;·&nbsp; {dups} dups dropped</span>
      </summary>
      <div class="run-body">
        <div class="section-head">📌 ALPACA NEWS — WATCHLIST TICKER NEWS</div>
        {_build_alpaca_section(alpaca)}
        <div class="section-head" style="margin-top:28px;">🌐 TAVILY — SECTOR CATALYST SWEEPS</div>
        {tavily_html}
      </div>
    </details>'''


def write_html_dashboard(all_runs: list, output_path: Path):
    """
    Overwrites YYYY-MM-DD.html with a dark-theme dashboard showing all runs for
    the day. Newest run is at the top (open by default); older runs are collapsed.
    Auto-refreshes every 60 seconds.
    """
    now_ct   = _now_ct()
    date_str = now_ct.strftime(f'%A %B {now_ct.day}, %Y')
    gen_ts   = now_ct.strftime('%I:%M %p CT').lstrip('0')
    today    = now_ct.strftime('%Y-%m-%d')

    # Render run cards newest-first (reverse the list for display)
    runs_reversed = list(reversed(all_runs))
    total_runs    = len(all_runs)
    cards_html    = ''
    for i, run in enumerate(runs_reversed):
        # Pass original idx so we know which is latest (last in the original list)
        orig_idx   = total_runs - 1 - i
        cards_html += _build_run_card(run, orig_idx, total_runs)

    if not all_runs:
        cards_html = '<p style="color:#8b949e;padding:20px;">No scan runs found for today.</p>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script>
    // Smart refresh: every 60 min, but OFF during weekend blackout
    // Blackout: Friday 3:00 PM CT through Sunday 4:30 PM CT
    (function() {{
      function inBlackout() {{
        var now  = new Date();
        var day  = now.getDay(); // 0=Sun,1=Mon,...,5=Fri,6=Sat
        var mins = now.getHours() * 60 + now.getMinutes();
        if (day === 6) return true;                          // all Saturday
        if (day === 5 && mins >= 15 * 60) return true;      // Fri >= 3:00 PM
        if (day === 0 && mins < 16 * 60 + 30) return true;  // Sun < 4:30 PM
        return false;
      }}
      if (!inBlackout()) {{
        setTimeout(function() {{ location.reload(); }}, 60 * 60 * 1000); // 60 min
      }}
    }})();
  </script>
  <title>War Room News Flow — {today}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: radial-gradient(circle at top, #162236 0%, #0d1117 46%, #080b10 100%);
      color: #e6edf3;
      font-family: "Segoe UI", Arial, sans-serif;
      min-height: 100vh;
    }}
    a {{ color: #42a5f5; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .wrap {{ max-width: 1440px; margin: 0 auto; padding: 28px 24px 60px; }}

    /* ── Header ── */
    .hero {{ margin-bottom: 28px; }}
    .hero h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.3px; }}
    .hero-sub {{ margin-top: 6px; color: #8b949e; font-size: 14px; }}
    .hero-meta {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; align-items: center; }}
    .stamp {{
      display: inline-flex; padding: 6px 12px; border-radius: 999px;
      border: 1px solid #30363d; color: #42a5f5; font-size: 11px;
      letter-spacing: 0.8px; text-transform: uppercase;
    }}
    .stamp-refresh {{
      display: inline-flex; padding: 6px 12px; border-radius: 999px;
      border: 1px solid #30363d; color: #8b949e; font-size: 11px;
      letter-spacing: 0.8px; text-transform: uppercase;
    }}
    .run-count {{
      display: inline-flex; padding: 6px 12px; border-radius: 999px;
      background: rgba(66,165,245,0.1); border: 1px solid rgba(66,165,245,0.3);
      color: #42a5f5; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;
    }}

    /* ── Schedule bar ── */
    .schedule-bar {{
      display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px;
    }}
    .sched-pill {{
      padding: 5px 14px; border-radius: 999px; font-size: 12px; font-weight: 600;
      border: 1px solid #30363d; color: #8b949e; letter-spacing: 0.4px;
    }}
    .sched-pill.done {{ border-color: #26a69a; color: #26a69a; background: rgba(38,166,154,0.08); }}
    .sched-pill.next {{ border-color: #42a5f5; color: #42a5f5; background: rgba(66,165,245,0.08); }}

    /* ── Run card ── */
    .run-card {{
      background: linear-gradient(180deg, rgba(22,27,34,0.96) 0%, rgba(13,17,23,0.98) 100%);
      border: 1px solid #30363d;
      border-radius: 16px;
      margin-bottom: 16px;
      overflow: hidden;
    }}
    .run-card[open] {{ border-color: #42a5f5; }}
    .run-summary {{
      display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
      padding: 16px 20px; cursor: pointer; list-style: none; user-select: none;
    }}
    .run-summary::-webkit-details-marker {{ display: none; }}
    .run-summary::before {{
      content: "▶"; font-size: 10px; color: #8b949e; transition: transform 0.15s;
    }}
    .run-card[open] > .run-summary::before {{ transform: rotate(90deg); }}
    .run-time {{ font-size: 18px; font-weight: 700; color: #e6edf3; }}
    .badge-latest {{
      padding: 3px 9px; border-radius: 999px; font-size: 10px; font-weight: 700;
      letter-spacing: 1px; text-transform: uppercase;
      background: rgba(66,165,245,0.15); border: 1px solid #42a5f5; color: #42a5f5;
    }}
    .run-stats {{ color: #8b949e; font-size: 12px; margin-left: auto; }}

    .run-body {{ padding: 0 20px 24px; border-top: 1px solid #21262d; }}

    /* ── Section headers ── */
    .section-head {{
      font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
      color: #8b949e; margin: 20px 0 12px; padding-bottom: 6px;
      border-bottom: 1px solid #21262d;
    }}

    /* ── Alpaca table ── */
    .news-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .news-table thead tr {{ border-bottom: 1px solid #30363d; }}
    .news-table th {{
      text-align: left; padding: 8px 10px; font-size: 10px; font-weight: 700;
      letter-spacing: 0.8px; text-transform: uppercase; color: #8b949e;
    }}
    .news-table td {{ padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: top; }}
    .news-table tr:last-child td {{ border-bottom: none; }}
    .ticker-cell {{ font-weight: 700; color: #42a5f5; white-space: nowrap; font-size: 12px; }}
    .meta-cell {{ color: #8b949e; font-size: 11px; white-space: nowrap; }}

    /* ── Tavily categories ── */
    .cat-block {{ margin-bottom: 20px; }}
    .cat-label {{
      font-size: 11px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .article-row {{
      display: flex; flex-direction: column; gap: 2px;
      padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    }}
    .article-row:last-child {{ border-bottom: none; }}
    .article-headline {{ font-size: 13px; color: #e6edf3; line-height: 1.4; }}
    .article-headline:hover {{ color: #42a5f5; }}
    .article-meta {{ font-size: 11px; color: #8b949e; }}

    .empty {{ color: #8b949e; font-size: 12px; padding: 8px 0; font-style: italic; }}

    /* ── Footer ── */
    .footer {{
      margin-top: 40px; padding-top: 16px; border-top: 1px solid #21262d;
      color: #8b949e; font-size: 11px; letter-spacing: 0.4px;
    }}
  </style>
</head>
<body>
  <div class="wrap">

    <div class="hero">
      <h1>War Room News Flow</h1>
      <div class="hero-sub">{_h(date_str)} &nbsp;·&nbsp; Pre-market catalyst feed</div>
      <div class="hero-meta">
        <span class="stamp">Generated {_h(gen_ts)}</span>
        <span class="stamp-refresh">Auto-refresh: 60 min (off weekends)</span>
        <span class="run-count">{total_runs} run{"s" if total_runs != 1 else ""} today</span>
      </div>
    </div>

    {_build_schedule_bar(all_runs, now_ct)}

    {cards_html}

    <div class="footer">
      QuantLab Data Lab &nbsp;·&nbsp; Scans: 6:30 AM / 7:30 AM / 8:06 AM CT (Mon–Fri) &nbsp;·&nbsp; Page refreshes every 60 min (off Fri 3 PM – Sun 4:30 PM CT)
    </div>

  </div>
</body>
</html>'''

    output_path.write_text(html, encoding='utf-8')


def _build_schedule_bar(all_runs: list, now_ct: datetime) -> str:
    """Show the 3 scheduled runs with done/next/pending styling."""
    run_labels = {r.get('run_label', '') for r in all_runs}

    def _classify(label: str) -> str:
        if label in run_labels:
            return 'done'
        # Check if this slot is the next upcoming one
        slot_map = {'6:30 AM CT': 6 * 60 + 30, '7:30 AM CT': 7 * 60 + 30, '8:06 AM CT': 8 * 60 + 6}
        current_mins = now_ct.hour * 60 + now_ct.minute
        slot_mins = slot_map.get(label, 0)
        if slot_mins > current_mins:
            # Find if it's the earliest upcoming
            pending_slots = [s for s, m in slot_map.items() if s not in run_labels and m > current_mins]
            if pending_slots and label == min(pending_slots, key=lambda s: slot_map[s]):
                return 'next'
        return ''

    slots = ['6:30 AM CT', '7:30 AM CT', '8:06 AM CT']
    pills = ''
    for slot in slots:
        cls = _classify(slot)
        icon = '✓ ' if cls == 'done' else ('→ ' if cls == 'next' else '')
        pills += f'<span class="sched-pill {cls}">{icon}{_h(slot)}</span>'

    return f'<div class="schedule-bar">{pills}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — TERMINAL CONFIRMATION
# ─────────────────────────────────────────────────────────────────────────────
def print_summary(tiingo_count, tavily_count, dups_dropped, total, output_path):
    today_str = _now_ct().strftime('%Y-%m-%d')
    print(f'\nNews_flow updated → News_flow/{today_str}.md + .html')
    print(f'   Alpaca: {tiingo_count} | Tavily: {tavily_count} | Deduped: {dups_dropped} | Total: {total}')
    print(f'   File: {output_path}')

    if tiingo_count == 0:
        print('\nWARNING: Alpaca News returned 0 results — check keys in shared/config/keys/live.env')
    if tavily_count == 0:
        print('\nWARNING: Tavily returned 0 results — check API key')


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────
def main():
    today_str    = _now_ct().strftime('%Y-%m-%d')
    output_md    = NEWS_FLOW / f'{today_str}.md'
    output_html  = NEWS_FLOW / f'{today_str}.html'
    output_cache = NEWS_FLOW / f'{today_str}.json'

    print(f'\n-- QuantLab News Scanner ----------------------------------')
    print(f'   Date: {today_str} | Output: {output_md}')
    print(f'-----------------------------------------------------------\n')

    # Step 1: Alpaca ticker news
    print('[1/5] Pulling Alpaca watchlist news...')
    tiingo_raw = fetch_tiingo_news()
    print(f'      Raw: {len(tiingo_raw)} items')

    # Step 2: Tavily
    print('[2/5] Running Tavily sector sweeps...')
    tavily_raw = fetch_tavily_news()
    tavily_raw_count = sum(len(v) for v in tavily_raw.values())
    print(f'      Raw: {tavily_raw_count} items across {len(TAVILY_QUERIES)} patterns')

    # Step 3: Dedup
    print('[3/5] Deduplicating...')
    tiingo_deduped, tiingo_dups = deduplicate_tiingo(tiingo_raw)
    tavily_deduped, tavily_dups = deduplicate_tavily(tavily_raw)
    total_dups = tiingo_dups + tavily_dups
    print(f'      Dropped {total_dups} duplicates')

    # Step 4: Write markdown (append) + JSON sidecar + HTML (overwrite)
    print('[4/5] Writing markdown...')
    write_markdown(
        tiingo_items      = tiingo_deduped,
        tavily_by_pattern = tavily_deduped,
        tiingo_raw_count  = len(tiingo_raw),
        tavily_raw_count  = tavily_raw_count,
        dups_dropped      = total_dups,
        output_path       = output_md,
    )

    print('[5/5] Saving cache + generating HTML dashboard...')
    all_runs = save_run_to_cache(
        cache_path     = output_cache,
        alpaca_items   = tiingo_deduped,
        tavily_by_pattern = tavily_deduped,
        dups_dropped   = total_dups,
    )
    write_html_dashboard(all_runs, output_html)
    print(f'      Dashboard: {output_html}')

    total = len(tiingo_deduped) + sum(len(v) for v in tavily_deduped.values())
    print_summary(
        tiingo_count = len(tiingo_deduped),
        tavily_count = sum(len(v) for v in tavily_deduped.values()),
        dups_dropped = total_dups,
        total        = total,
        output_path  = output_md,
    )


if __name__ == '__main__':
    main()

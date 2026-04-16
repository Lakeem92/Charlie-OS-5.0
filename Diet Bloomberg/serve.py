"""
QuantLab Terminal Server v2.0
Serves the Personal Intelligence Platform dashboard on port 8766.
Jinja2-powered templating with JSON data from collectors.
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import os
import json
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / 'templates'
STATIC = ROOT / 'static'
DATA_LAB = ROOT.parent
CATALYST_DB = DATA_LAB / 'catalyst_analysis_db'

NEWS_FLOW = DATA_LAB / 'News_flow'
PORT = 8766

# ── Jinja2 environment ───────────────────────────────────────────────────────
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=False,  # HTML templates manage their own escaping
)
jinja_env.filters['tojson'] = lambda v: json.dumps(v, default=str)


def _load_json(subdir: str, filename: str = 'latest.json') -> dict:
    """Load a collector's JSON output. Returns empty dict if missing."""
    path = CATALYST_DB / subdir / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_news_flow() -> dict | None:
    """Load today's News_flow JSON (from scan_news.py) and transform to template schema."""
    today_file = NEWS_FLOW / f'{datetime.now().strftime("%Y-%m-%d")}.json'
    if not today_file.exists():
        return None
    try:
        raw = json.loads(today_file.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None

    # News_flow is a list of feed run objects; find the focus feed
    focus_articles = []
    for run in (raw if isinstance(raw, list) else [raw]):
        if run.get('feed_name') != 'focus':
            continue
        for item in run.get('alpaca_items', []) + run.get('official_items', []):
            ticker_raw = item.get('ticker', '')
            tickers = [t.strip() for t in ticker_raw.split(',') if t.strip()] if isinstance(ticker_raw, str) else (ticker_raw or [])
            focus_articles.append({
                'title': item.get('headline', ''),
                'url': item.get('url', ''),
                'source': item.get('source', ''),
                'published': item.get('published_at', ''),
                'tickers': tickers,
                'description': '',
            })

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in focus_articles:
        if a['url'] and a['url'] not in seen:
            seen.add(a['url'])
            unique.append(a)
    unique.sort(key=lambda x: x.get('published', ''), reverse=True)

    return {
        'focus_news': unique,
        'counts': {'focus': len(unique)},
        'news_flow_ts': run.get('run_label', '') if raw else '',
    }


# ── Route → template + data source mapping ───────────────────────────────────
ROUTE_CONFIG = {
    '':           {'template': 'macro.html',       'data': [('macro_regime', 'latest.json')]},
    '/today':     {'template': 'macro.html',       'data': [('macro_regime', 'latest.json')]},
    '/macro':     {'template': 'macro.html',       'data': [('macro_regime', 'latest.json')]},
    '/ai':        {'template': 'ai_cascade.html',  'data': [('daily_briefing', 'ai_cascade.json')]},
    '/etf':       {'template': 'etf_monitor.html', 'data': [('etf_structural', 'latest.json')]},
}



def _build_page_context(route: str) -> dict:
    """Build the full template context for a route."""
    cfg = ROUTE_CONFIG.get(route, {})
    ctx = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M CT'),
    }
    sources = cfg.get('data', [])
    # Load each data source — merge into context
    for i, (subdir, filename) in enumerate(sources):
        envelope = _load_json(subdir, filename)
        key = Path(filename).stem
        data = envelope.get('data', {})
        updated = envelope.get('updated_at', '')
        # First source (or 'latest') always populates 'd' for template convenience
        if i == 0 or key == 'latest':
            ctx['d'] = data
            ctx['updated_at'] = updated
        # Named sources also get their own key (commodities, crypto, etc.)
        if key != 'latest':
            ctx[key] = data
            ctx[f'{key}_updated'] = updated
    # Ensure 'd' always exists
    if 'd' not in ctx:
        ctx['d'] = {}

    # ── News route: merge News_flow focus list data (from scan_news.py) ───
    if route == '/news':
        nf = _load_news_flow()
        if nf:
            # News_flow focus articles take priority over stale news.json
            ctx['d']['focus_news'] = nf['focus_news']
            ctx['d'].setdefault('counts', {})
            ctx['d']['counts']['focus'] = nf['counts']['focus']

    return ctx


# ── HTTP Handler ──────────────────────────────────────────────────────────────
class QuietHandler(SimpleHTTPRequestHandler):
    """Custom handler with routing and suppressed request logging."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # ── Static files ──────────────────────────────────────────────────
        if path.startswith('/static/'):
            rel = path[len('/static/'):]
            file_path = STATIC / rel
            if file_path.exists() and file_path.is_file():
                self._serve_file(file_path)
                return
            self.send_error(404)
            return

        # ── HTML routes ───────────────────────────────────────────────────
        if path in ROUTE_CONFIG:
            cfg = ROUTE_CONFIG[path]
            try:
                template = jinja_env.get_template(cfg['template'])
                ctx = _build_page_context(path)
                html = template.render(**ctx)
            except Exception as e:
                html = f"<pre>Template error: {e}</pre>"
            self._send_html(html)
            return

        # ── Fallback ──────────────────────────────────────────────────────
        self.send_error(404, f"Route not found: {path}")

    def _send_html(self, html: str):
        """Send an HTML response."""
        encoded = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_file(self, filepath: Path):
        """Serve a static file (CSS, JS, images)."""
        ext = filepath.suffix.lower()
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff2': 'font/woff2',
            '.woff': 'font/woff',
        }
        mime = mime_types.get(ext, 'application/octet-stream')
        data = filepath.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', f'{mime}; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='QuantLab Terminal Server')
    parser.add_argument('--port', type=int, default=PORT, help='Port to listen on')
    parser.add_argument('--dry-run', action='store_true', help='Print config and exit without starting')
    args = parser.parse_args()

    if args.dry_run:
        print(f"QuantLab Terminal Server v2.0 (Jinja2)")
        print(f"  Port: {args.port}")
        print(f"  Templates: {TEMPLATES}")
        print(f"  Static: {STATIC}")
        print(f"  Catalyst DB: {CATALYST_DB}")
        print(f"  Routes: {', '.join(k or '/' for k in ROUTE_CONFIG.keys())}")
        # Test Jinja2 can load all templates
        for cfg in ROUTE_CONFIG.values():
            t = cfg['template']
            try:
                jinja_env.get_template(t)
                print(f"  OK  {t}")
            except Exception as e:
                print(f"  ERR {t}: {e}")
        print(f"  Status: DRY RUN — would start on http://localhost:{args.port}")
        return

    server = HTTPServer(('0.0.0.0', args.port), QuietHandler)
    print(f"""
{'='*56}
 QUANTLAB TERMINAL v2.0
{'='*56}
 Dashboard:    http://localhost:{args.port}
   Macro:      http://localhost:{args.port}/macro
   AI Cascade: http://localhost:{args.port}/ai
   ETF:        http://localhost:{args.port}/etf
   Focus List: http://localhost:{args.port}/focus
   News:       http://localhost:{args.port}/news
 Catalyst DB:  {CATALYST_DB}
 Focus List:   {DATA_LAB / 'watchlists' / 'focus_list.csv'}
{'='*56}
 Server running. Press Ctrl+C to stop.
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == '__main__':
    main()

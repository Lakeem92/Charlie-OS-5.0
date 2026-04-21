"""Quick render test for all 7 templates with correct data routing."""
import sys, json
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

ROOT = Path(r'C:\QuantLab\Data_Lab\terminal')
DB = Path(r'C:\QuantLab\Data_Lab\catalyst_analysis_db')
env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=False)
env.filters['tojson'] = lambda v: json.dumps(v, default=str)

ROUTES = {
    'macro':       ('macro.html',       [('macro_regime', 'latest.json')]),
    'etf':         ('etf_monitor.html',  [('etf_structural', 'latest.json')]),
    'catalysts':   ('catalysts.html',    [('daily_briefing', 'catalysts.json')]),
    'focus':       ('focus_list.html',   [('focus_list', 'latest.json')]),
    'ai':          ('ai_cascade.html',   [('daily_briefing', 'ai_cascade.json')]),
    'commodities': ('commodities.html',  [('macro_regime', 'commodities.json'), ('macro_regime', 'crypto.json')]),
    'news':        ('news.html',         [('daily_briefing', 'news.json')]),
}

for name, (tmpl, sources) in ROUTES.items():
    ctx = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M CT'), 'd': {}}
    for i, (subdir, fn) in enumerate(sources):
        p = DB / subdir / fn
        if p.exists():
            raw = json.loads(p.read_text(encoding='utf-8'))
            key = Path(fn).stem
            data = raw.get('data', {})
            # First source always goes into 'd'
            if i == 0 or key == 'latest':
                ctx['d'] = data
                ctx['updated_at'] = raw.get('updated_at', '')
            # Named sources also get their own key
            if key != 'latest':
                ctx[key] = data
        else:
            print(f"  WARN: {p} not found")

    try:
        html = env.get_template(tmpl).render(**ctx)
        vis = []
        if 'heatmap-cell' in html: vis.append('heatmap')
        if 'glow-' in html: vis.append('glow')
        if 'badge' in html: vis.append('badges')
        if 'alert-banner' in html: vis.append('alert')
        if 'intel-grid' in html: vis.append('intel-cards')
        if 'gauge-circle' in html: vis.append('gauge')
        if 'flow-bar' in html: vis.append('flow-bars')
        if 'timeline-item' in html: vis.append('timeline')
        if 'sparkline' in html: vis.append('sparklines')
        if 'vix-meter' in html: vis.append('vix-gauge')
        if 'new Chart' in html: vis.append('chart.js')
        if 'OPEX WEEK' in html: vis.append('OPEX-alert')
        print(f"  OK  {name:12s} {len(html):>7,} chars | {', '.join(vis) if vis else '(basic)'}")
    except Exception as e:
        print(f"  FAIL {name:12s} {e}")

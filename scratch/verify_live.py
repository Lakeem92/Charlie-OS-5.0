"""Verifies all 7 dashboard pages render with visual elements via live server."""
import sys
import re
from urllib.request import urlopen

PAGES = {
    'macro':       ('http://localhost:8766/macro',       ['heatmap-cell', 'vix-meter', 'regime']),
    'etf':         ('http://localhost:8766/etf',         ['heatmap-cell', 'data-table']),
    'catalysts':   ('http://localhost:8766/catalysts',   ['badge', 'timeline', 'OPEX', 'earnings-card']),
    'focus':       ('http://localhost:8766/focus',       ['intel-card', 'sparkline', 'Chart(']),
    'ai':          ('http://localhost:8766/ai',          ['score-4', 'flow-bar', 'ALL FLOWS', 'gauge-circle']),
    'commodities': ('http://localhost:8766/commodities', ['card', 'data-table']),
    'news':        ('http://localhost:8766/news',        ['article', 'news']),
}

all_ok = True
for name, (url, checks) in PAGES.items():
    try:
        html = urlopen(url).read().decode('utf-8')
        found = [c for c in checks if c in html]
        missing = [c for c in checks if c not in html]
        status = 'PASS' if not missing else 'PARTIAL'
        if missing:
            all_ok = False
        print(f"  {'✅' if not missing else '⚠️'} {name:12s} {len(html):>7,} chars | found: {', '.join(found)} {'| MISSING: ' + ', '.join(missing) if missing else ''}")
    except Exception as e:
        all_ok = False
        print(f"  ❌ {name:12s} ERROR: {e}")

print(f"\n{'🎉 ALL 7 PAGES VERIFIED!' if all_ok else '⚠️ Some issues found'}")

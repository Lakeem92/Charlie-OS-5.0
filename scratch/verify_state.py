"""Verify all visual elements exist in CSS and templates."""
from pathlib import Path

# Check CSS
css = Path(r'C:\QuantLab\Data_Lab\terminal\static\style.css').read_text(encoding='utf-8')
visuals = ['pulse-glow', 'heatmap-cell', 'gauge-circle', 'flow-bar', 'intel-card',
           'vix-meter', 'alert-banner', 'timeline-item', 'sparkline', 'badge-green']
print("=== CSS Visual Classes ===")
for v in visuals:
    found = v in css
    print(f"  {'YES' if found else 'NO ':>3}  {v}")
print(f"\n  CSS total: {len(css):,} chars")

# Check templates for key visual elements
print("\n=== Template Visual Elements ===")
tdir = Path(r'C:\QuantLab\Data_Lab\terminal\templates')
checks = {
    'macro.html': ['heatmap-cell', 'vix-meter', 'regime'],
    'etf_monitor.html': ['heatmap-cell'],
    'catalysts.html': ['alert-banner', 'timeline-item', 'earnings-card', 'badge'],
    'focus_list.html': ['intel-card', 'sparkline', 'new Chart'],
    'ai_cascade.html': ['gauge-circle', 'flow-bar', 'heatmap-cell'],
    'commodities.html': ['card'],
    'news.html': ['article'],
}
for fname, elements in checks.items():
    html = (tdir / fname).read_text(encoding='utf-8')
    found = [e for e in elements if e in html]
    missing = [e for e in elements if e not in html]
    status = 'PASS' if not missing else 'FAIL'
    print(f"  {status:>4}  {fname:22s}  found: {', '.join(found)}", end='')
    if missing:
        print(f"  MISSING: {', '.join(missing)}", end='')
    print()

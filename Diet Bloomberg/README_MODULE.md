# Terminal Module

Flask/HTTP server serving the QuantLab Personal Intelligence Platform dashboard.

- **Port:** 8766
- **Entry point:** `serve.py`
- **Templates:** `templates/` (Jinja2 HTML)
- **Static assets:** `static/` (CSS, JS)

## Routes
| Path | Page |
|------|------|
| `/` | Redirect to `/macro` |
| `/macro` | Macro Intelligence |
| `/ai` | AI Supercycle Monitor |
| `/etf` | ETF Structural + Momentum |
| `/catalysts` | Catalyst Intelligence |
| `/focus` | Focus List Intelligence |
| `/commodities` | Commodities + Crypto |
| `/news` | News Flow |

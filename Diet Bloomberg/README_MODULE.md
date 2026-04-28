# Terminal Module

Jinja2/HTTP server for the Diet Bloomberg dashboard.

- **Port:** `8766`
- **Entry point:** `Diet Bloomberg/serve.py`
- **Startup wrapper:** `scripts/startup_diet_bloomberg.py`
- **Templates:** `Diet Bloomberg/templates/`
- **Static assets:** `Diet Bloomberg/static/`
- **Main context doc:** `Diet Bloomberg/README.md`

## Live Routes
| Path | Page |
|------|------|
| `/` | Macro Intelligence |
| `/macro` | Macro Intelligence |
| `/ai` | AI Supercycle Monitor |
| `/etf` | ETF Structural + Momentum |
| `/news` | News Flow |
| `/health` | Render health check for all live pages |

Collector outputs are refreshed by `run_all.py` and loaded from `catalyst_analysis_db/`.

# Studies Infrastructure

## Overview
The studies infrastructure provides a **natural-language router** that maps user queries to predefined quantitative studies. This mirrors the Levels Engine pattern in `tools/levels_engine/route_query.py`.

## How to Use the Router

```bash
# From repo root:
python tools/studies/route_study.py "trend vs chop in uptrend for NVDA" --tickers NVDA TSLA --start 2018-01-01 --end 2026-02-15 --intraday false

# Minimal (uses study defaults):
python tools/studies/route_study.py "gap up close strong"
```

### CLI Arguments
| Argument      | Required | Description                          |
|---------------|----------|--------------------------------------|
| `query`       | Yes      | Natural language query string        |
| `--tickers`   | No       | Space-separated ticker list          |
| `--start`     | No       | Start date (YYYY-MM-DD)             |
| `--end`       | No       | End date (YYYY-MM-DD)               |
| `--intraday`  | No       | `true` or `false`                   |

## How to Add a New Study

1. **Copy the template:**
   ```bash
   cp -r studies/_TEMPLATE studies/my_new_study
   ```

2. **Edit files** in `studies/my_new_study/`:
   - `config.yaml` — locked parameters for your study
   - `collect_data.py` — data fetching logic
   - `analyze.py` (or multiple `analyze_*.py`) — analysis scripts
   - `utils.py` — study-specific helpers
   - `run_study.py` — orchestrator that runs collect + analyze

3. **Register in `tools/studies/studies_registry.yaml`:**
   ```yaml
   studies:
     my_new_study:
       description: "What this study measures"
       keywords:
         - "keyword one"
         - "keyword two"
       entrypoint: "studies/my_new_study/run_study.py"
       scripts:
         - "collect_data.py"
         - "analyze_something.py"
   ```

4. **Test:**
   ```bash
   python tools/studies/route_study.py "keyword one query" --tickers SPY
   ```

## Expected Study Folder Structure
Every study folder must follow this layout (matching `_TEMPLATE`):

```
studies/<study_name>/
  README.md
  config.yaml
  tickers.txt          (optional)
  collect_data.py
  analyze_*.py         (one or more)
  utils.py
  run_study.py
  outputs/
    data/              (raw CSV files)
    tables/            (analysis result CSVs)
    charts/            (matplotlib PNGs)
    summary/           (run_log.txt, markdown summaries)
```

## Design Principles
- **Deterministic:** No randomness, no opinions, no trade advice.
- **Locked parameters:** All thresholds defined in config.yaml.
- **Reproducible:** Same inputs → same outputs.
- **Data source priority:** Alpaca preferred, yfinance fallback with warning.

# ask.py - English Entrypoint for Studies

**Zero flags. Just type your question.**

## Usage

```bash
python tools/studies/ask.py "<your question>"
```

## Example Queries

### Trend vs Chop + Forward Horizons
```bash
python tools/studies/ask.py "when NVDA gaps up 5%+ does it trend or chop and what's the win rate D5-D10"
```
Parses: NVDA, gap_up event (>= 5%), horizons [5,6,7,8,9,10], trend_chop + gap_close_strength + forward_horizons modules.

### Simple Trend/Chop Mix
```bash
python tools/studies/ask.py "trend vs chop mix for AAPL in uptrends"
```
Parses: AAPL, trend_chop_mix module only, default 5-year lookback.

### Gap-Up Close Strength
```bash
python tools/studies/ask.py "gap up 3-5% close strong probability for TSLA"
```
Parses: TSLA, gap_up event (3-5% bin), gap_close_strength module.

### Multi-Ticker Forward Returns
```bash
python tools/studies/ask.py "NVDA TSLA AAPL gap up 2%+ D5 D10 win rate over 2020 to 2024"
```
Parses: 3 tickers, gap_up >= 2%, horizons [5,10], forward_horizons module, date range 2020-01-01 to 2024-12-31.

### First-Hour Intraday Analysis
```bash
python tools/studies/ask.py "NVDA first hour VWAP hold after gap up intraday"
```
Parses: NVDA, gap_up event, intraday enabled, first_hour module.

## What Happens Under the Hood

1. `ask.py` sends your question to `nl_parse.py` (deterministic parser -- no LLM)
2. Parser extracts: tickers, event type, thresholds, horizons, metrics, date range, intraday flag
3. A `run_spec.yaml` is written to `outputs/summary/`
4. `route_study.py` matches keywords to a study in the registry
5. `run_study.py --spec run_spec.yaml` executes only the modules you need

## Run Spec Schema

The parser produces a YAML spec like:

```yaml
query: "when NVDA gaps up 5%+ does it trend or chop and what's the win rate D5-D10"
study: trend_chop_gap_quality
tickers: [NVDA]
date_range:
  start: "2020-01-01"
  end: "2025-06-01"
event:
  type: gap_up
  gap_up_min: 0.05
intraday:
  enabled: false
forward_horizons:
  horizons: [5, 6, 7, 8, 9, 10]
  window: 10
  metrics: [win_rate, avg_return, median_return]
outputs:
  include_trend_chop_mix: true
  include_gap_close_strength: true
  include_intraday_first_hour: false
  include_forward_horizons: true
```

## Adding New Studies

1. Add entry to `tools/studies/studies_registry.yaml` with keywords
2. Create study folder from `studies/_TEMPLATE/`
3. Implement `run_study.py --spec <path>` in the new study
4. `ask.py` will route to it automatically based on keyword matches

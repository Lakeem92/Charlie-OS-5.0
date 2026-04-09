# trend_chop_gap_quality

## Purpose

Quantify day-type mix during uptrend regimes, measure gap-up close strength by size bin, classify intraday first-hour action, and compute forward horizon returns for event days.

---

## Four Core Analyses

| # | Analysis | Description |
|---|----------|-------------|
| 1 | **Trend vs Chop** | What fraction of uptrend-regime days are clean trend days vs choppy days? |
| 2 | **Gap-Up Close Strength** | When a stock gaps up, how often does it close strong vs weak? Broken out by gap size bin. |
| 3 | **Intraday First-Hour Classifier** | Is the first hour trending, fading, or chopping? Scored 0–5 on a failure rubric. |
| 4 | **Forward Horizon Returns** | For event days (e.g., gap-up), compute returns at D1, D2, D5, D10 and analyze win rates. |

---

## Study Components

### Scripts

| Script | Purpose |
|--------|---------|
| `run_study.py` | Orchestrates full pipeline — collects data, runs all analyses, manages run archives |
| `collect_data.py` | Fetches daily (and optional intraday) price data via Alpaca/yfinance |
| `analyze_trend_chop.py` | Analysis 1 — Classifies uptrend days as TREND_BULL / CHOP / NEUTRAL |
| `analyze_gapup_close_strength.py` | Analysis 2 — Gap-up day close strength probabilities by gap size bin |
| `analyze_intraday_first_hour.py` | Analysis 3 — First-hour VWAP hold, OR break time, failure score, signature classification |
| `analyze_forward_horizons.py` | Analysis 4 — Forward close-to-close returns at configurable horizons |
| `utils.py` | Shared indicator calculations (ATR, SMA, CLV, VWAP, gap_pct, etc.) |

### Configuration Files

| File | Purpose |
|------|---------|
| `config.yaml` | **LOCKED** parameters for all analyses — thresholds, bins, regime rules |
| `tickers.txt` | Default ticker list (one per line, `#` comments supported) |

---

## Locked Definitions

All thresholds are in `config.yaml` and **must not be modified** for reproducibility.

### Core Indicators

| Parameter | Value | Description |
|-----------|-------|-------------|
| ATR length | 14 | Average True Range lookback |
| SMA length | 20 | Simple Moving Average for regime detection |
| SMA slope lookback | 5 | Bars to measure SMA slope |

### Uptrend Regime (Method A)

```
uptrend = (close > SMA20) AND (SMA20_today > SMA20_5_bars_ago)
```

### Trend Day Classification

| Parameter | Value | Description |
|-----------|-------|-------------|
| Trend CLV min | 0.80 | Close Location Value threshold (1.0 = closed at high) |
| Trend Range/ATR min | 1.00 | Day range must exceed ATR |
| Trend requires green | true | close > open required |

### Chop Day Classification

| Parameter | Value | Description |
|-----------|-------|-------------|
| Chop Range/ATR max | 0.80 | Below this = chop |
| Chop Body% max | 0.35 | Body less than 35% of range = chop |

### Gap-Up Close Strength

| Parameter | Value | Description |
|-----------|-------|-------------|
| Gap bins | 1%, 3%, 5%, 8%, 12%, 20% | Size buckets |
| CloseStrong | CLV ≥ 0.80 AND Range/ATR ≥ 1.00 | Strong close criteria |
| CloseWeak | CLV ≤ 0.30 OR close < open | Weak close criteria |

### First-Hour Failure Score (0–5)

Each condition adds +1 to the failure score:

| Condition | Threshold |
|-----------|-----------|
| VWAP hold | < 0.50 (less than 50% of bars above VWAP) |
| Reclaim count | ≥ 2 (crossed VWAP from below 2+ times) |
| First-hour CLV | < 0.55 |
| OR break time | > 40 minutes |
| Pullback depth | > 0.50 |

### Intraday Signatures

| Signature | Criteria |
|-----------|----------|
| **TrendSignature** | vwap_hold ≥ 0.80 AND pullback_depth ≤ 0.35 AND firsthour_clv ≥ 0.75 |
| **FadeSignature** | vwap_hold < 0.50 AND reclaim_count ≥ 2 AND firsthour_clv ≤ 0.55 |
| **ChopSignature** | All other days |

---

## CLI Usage

### Full Pipeline via `run_study.py`

```bash
cd studies/trend_chop_gap_quality

# Daily only (default)
python run_study.py --tickers NVDA TSLA --start 2018-01-01

# With intraday analysis
python run_study.py --tickers NVDA TSLA --start 2018-01-01 --intraday true

# Custom date range
python run_study.py --tickers AAPL --start 2020-01-01 --end 2025-12-31

# Use default tickers from tickers.txt
python run_study.py

# Use a run_spec.yaml for full control
python run_study.py --spec outputs/summary/run_spec.yaml
```

### Via Router (Natural Language)

```bash
python tools/studies/route_study.py "trend vs chop in uptrend for NVDA" --tickers NVDA --intraday true
python tools/studies/route_study.py "gap up close strong by gap size"
python tools/studies/route_study.py "first hour failure score" --tickers TSLA --intraday true
```

### Individual Scripts

```bash
# Step 1: Collect data
python collect_data.py --tickers NVDA --start 2020-01-01 --end 2025-12-31

# Step 2: Run analyses separately
python analyze_trend_chop.py
python analyze_gapup_close_strength.py
python analyze_intraday_first_hour.py  # Only if intraday CSVs exist
python analyze_forward_horizons.py      # Reads config from run_spec.yaml
```

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `--tickers` | Space-separated ticker symbols (overrides tickers.txt) |
| `--start` | Start date YYYY-MM-DD |
| `--end` | End date YYYY-MM-DD (default: today) |
| `--intraday` | Enable intraday 5Min data collection and analysis (`true`/`false`) |
| `--spec` | Path to run_spec.yaml (overrides all other args) |

---

## Ticker Resolution Priority

1. `--tickers` CLI argument
2. `tickers.txt` file in study folder
3. `tickers_default` in config.yaml

---

## Data Sources

| Priority | Source | Notes |
|----------|--------|-------|
| Primary | **Alpaca** | Requires API keys in environment; routes via DataRouter |
| Fallback | **yfinance** | Used if Alpaca fails; logged with WARNING; 5min limited to ~60 days |

---

## Output Structure

```
outputs/
  data/                               — Raw price CSVs
    {TICKER}_1D.csv                   — Daily OHLCV
    {TICKER}_5Min.csv                 — Intraday 5-minute bars (if enabled)
  tables/                             — Analysis results
    trend_chop_by_ticker.csv          — Per-ticker trend/chop/neutral counts
    trend_chop_aggregate.csv          — Cross-ticker aggregate stats
    gapup_stats_by_ticker.csv         — Gap-up close strength per ticker/bin
    gapup_stats_aggregate.csv         — Aggregate gap-up stats
    intraday_first_hour_by_day.csv    — Day-by-day first-hour metrics (if intraday)
    intraday_first_hour_summary_by_ticker.csv
    intraday_first_hour_summary_aggregate.csv
    forward_horizons_by_ticker.csv    — Forward returns per ticker (if enabled)
    forward_horizons_aggregate.csv    — Aggregate forward return stats
  charts/                             — Visualizations
    trend_chop_aggregate.png
    gapup_close_strong_by_bin.png
    intraday_signature_distribution.png (if intraday)
  summary/                            — Run metadata and summaries
    run_log.txt                       — Data source, warnings, runtime info
    run_spec.yaml                     — Exact parameters used
    trend_chop_summary.md
    gapup_summary.md
    intraday_first_hour_summary.md    (if intraday)
```

---

## Run Spec (YAML) Configuration

For advanced runs, create a `run_spec.yaml`:

```yaml
tickers:
  - NVDA
  - TSLA

date_range:
  start: "2020-01-01"
  end: "2025-12-31"

intraday:
  enabled: true

outputs:
  include_trend_chop_mix: true
  include_gap_close_strength: true
  include_intraday_first_hour: true
  include_forward_horizons: true

event:
  type: gap_up
  gap_up_min: 0.03       # 3%+ gaps only
  # gap_bin_label: "5-8%"  # Or filter to specific bin

forward_horizons:
  horizons: [1, 2, 5, 10]
  metrics:
    - win_rate_positive
    - avg_return
    - median_return
```

Run with:
```bash
python run_study.py --spec outputs/summary/run_spec.yaml
```

---

## Utility Functions (`utils.py`)

### Safe Math
- `safe_divide(a, b, default=0.0)` — Division with zero/NaN handling

### Core Indicators
- `true_range(high, low, close)` — True Range series
- `atr(high, low, close, length=14)` — Average True Range
- `sma(series, length=20)` — Simple Moving Average

### Price Structure
- `clv(high, low, close)` — Close Location Value (0.0 = low, 1.0 = high)
- `body_pct(open, high, low, close)` — Body as fraction of range
- `range_multiple(high, low, atr_series)` — Day range / ATR
- `gap_pct(open_today, close_prev)` — Overnight gap percentage

### Intraday
- `typical_price(high, low, close)` — (H + L + C) / 3
- `vwap(typical_price, volume)` — Cumulative VWAP
- `compute_daily_vwap(df_intraday)` — VWAP reset per day
- `first_hour_window(df_day, or_minutes=60)` — Extract first-hour bars
- `or_break_time_minutes(df_day, or_high)` — Minutes until OR high is broken
- `pullback_depth(df_first_hour, or_high, or_low)` — Depth after OR high printed
- `reclaim_count(close_series, vwap_series)` — Count VWAP reclaims

### Gap Bin Labelling
- `assign_gap_bin(gap_val, bins)` — Map gap % to label (e.g., "3-5%", "8-12%")

---

## Run Archive System

Every run creates a timestamped archive folder for reproducibility:

```
outputs/
  runs/
    2026-02-15_0732_NVDA_gap5p_D5-10_intra/
      data/           — Raw CSVs for this run
      tables/         — Analysis results
      charts/         — PNG charts
      summary/
        run_spec.yaml — Exact spec used
        run_log.txt   — Run details
        manifest.json — List of generated files
  LATEST.txt          — Points to most recent run folder
  latest/             — Symlink to most recent run (if supported)
```

### Run ID Format

`<timestamp>_<tickers>_<conditions>_<flags>`

Examples:
- `2026-02-15_0732_NVDA_gap5p_D5-10_intra`
- `2026-02-15_0800_TSLA-AAPL-MSFT`
- `2026-02-15_0815_MULTI_gap3p`

### Finding the Latest Run

```bash
# Read LATEST.txt
cat outputs/LATEST.txt
# Output: runs/2026-02-15_0732_NVDA_gap5p_D5-10_intra/

# Or use the symlink (if available)
ls outputs/latest/
```

### Backwards Compatibility

Key aggregate tables and summaries are also copied to the top-level `outputs/tables/` and `outputs/summary/` folders, so existing workflows that expect outputs there will continue to work.

### Collision Handling

If two runs happen in the same minute with identical parameters, suffixes are appended: `_02`, `_03`, etc.

---

## Analysis Details

### Analysis 1: Trend vs Chop

**Question:** During uptrend regimes, what mix of day types do we see?

**Method:**
1. Compute ATR(14), SMA(20), SMA slope over 5 bars
2. Filter to uptrend days: `close > SMA20 AND SMA20 rising`
3. Classify each day:
   - **TREND_BULL:** CLV ≥ 0.80, Range/ATR ≥ 1.00, green candle
   - **CHOP:** Range/ATR < 0.80 OR Body% < 0.35
   - **NEUTRAL:** everything else

**Output:** Percentage breakdown per ticker and aggregate.

---

### Analysis 2: Gap-Up Close Strength

**Question:** When a stock gaps up, does it close strong or weak? How does this vary by gap size?

**Method:**
1. Identify gap-up days (gap ≥ 1%)
2. Bin by gap size: 1-3%, 3-5%, 5-8%, 8-12%, 12-20%, 20%+
3. Compute per bin:
   - P(close_strong): CLV ≥ 0.80 AND Range/ATR ≥ 1.00
   - P(close_weak): CLV ≤ 0.30 OR red candle
   - Avg same-day, next-day, 2-day returns

**Output:** Probability tables and returns by gap bin.

---

### Analysis 3: Intraday First-Hour Classifier

**Question:** Does the first hour predict the day's outcome?

**Method:** (requires `--intraday true`)
1. Filter to RTH bars (9:30–16:00 ET)
2. For each day, compute:
   - **VWAP hold:** % of first-hour bars closing above VWAP
   - **OR break time:** Minutes until Opening Range high is exceeded
   - **First-hour CLV:** Where first hour closes within its range
   - **Pullback depth:** How far price dips after printing OR high
   - **Reclaim count:** How many times price crosses VWAP from below

3. Compute **Failure Score (0–5)** based on locked rules
4. Classify: TrendSignature / FadeSignature / ChopSignature

**Output:** Per-day metrics, signature distribution, failure score histogram.

---

### Analysis 4: Forward Horizon Returns

**Question:** What are forward returns after event days?

**Method:**
1. Identify event days (e.g., gap_up ≥ 3%)
2. Compute close-to-close returns at each horizon (D1, D2, D5, D10, etc.)
3. Calculate metrics:
   - Win rate (% positive)
   - Average return
   - Median return

**Output:** Forward return tables per horizon, aggregate stats.

---

## Environment Setup

```bash
# Activate venv
cd c:\QuantLab\Data_Lab
.\.venv\Scripts\Activate.ps1

# Ensure API keys are loaded
$env:ALPACA_API_KEY = "your_key"
$env:ALPACA_SECRET_KEY = "your_secret"
# Or load from .env via env_loader

# Run study
cd studies/trend_chop_gap_quality
python run_study.py --tickers NVDA TSLA --start 2020-01-01
```

---

## Notes

- **No trade advice.** All language is descriptive and conditional.
- **Reproducibility.** Outputs are deterministic given the same data.
- **Parameters are locked.** No tuning or curve-fitting.
- **RTH filter.** Intraday analysis uses Regular Trading Hours only (9:30–16:00 ET).
- **Timezone.** Analysis uses Central Time (CT) for session boundaries per lab conventions.

# Gap Bias + TSL3 Slope + RS(Z) Confluence Study

## What This Studies

Whether gap-down days with a **rising TSL3 slope at open** and **crushed relative strength** tend to reverse (close higher) or continue lower.

### The Hypothesis

When a stock gaps down significantly but shows:
1. **TSL3 slope is RISING on the 5-minute chart** at the market open (first 4 bars, 9:30-9:50 AM)
2. **RS(Z) vs SPY is ≤ -1.0** (oversold relative momentum, from prior daily close)

...it may signal "tired selling" and a potential intraday reversal (close > open).

## Quick Start

### 1. Install Dependencies

```bash
pip install yfinance pandas numpy scipy matplotlib seaborn
```

### 2. Configure Ticker

Edit `config.py`:
```python
TICKER = "QQQ"      # Change to any symbol (TSLA, AAPL, IWM, etc.)
BENCHMARK = "SPY"   # Benchmark for RS(Z) calculation
```

### 3. Run the Study

Run all scripts in order:

```bash
cd studies/gap_tsl_rs_confluence

# Collect data
python scripts/1_collect_data.py

# Calculate TSL3 indicator
python scripts/2_calculate_tsl3.py

# Calculate RS(Z) relative strength
python scripts/3_calculate_rs_z.py

# Identify gaps
python scripts/4_identify_gaps.py

# Detect confluence events
python scripts/5_detect_confluence_events.py

# Analyze forward returns
python scripts/6_analyze_forward_returns.py

# Run robustness analysis
python scripts/7_robustness_variants.py

# Generate final report
python scripts/8_generate_report.py
```

### 4. View Results

- **Report:** `outputs/reports/{TICKER}_gap_tsl_rs_study.md`
- **Heatmap:** `outputs/charts/{TICKER}_robustness_heatmap.png`
- **Tables:** `outputs/tables/`

## Folder Structure

```
gap_tsl_rs_confluence/
├── README.md               # This file
├── config.py               # All study parameters
├── scripts/
│   ├── 1_collect_data.py           # Download price data
│   ├── 2_calculate_tsl3.py         # Calculate TSL3 indicator
│   ├── 3_calculate_rs_z.py         # Calculate RS(Z)
│   ├── 4_identify_gaps.py          # Identify gap-down days
│   ├── 5_detect_confluence_events.py  # Find setup days
│   ├── 6_analyze_forward_returns.py   # Measure outcomes
│   ├── 7_robustness_variants.py    # Test parameter variations
│   └── 8_generate_report.py        # Generate summary report
├── data/
│   ├── raw/               # Downloaded price data
│   └── processed/         # Calculated indicators
├── outputs/
│   ├── charts/            # Visualizations
│   ├── tables/            # CSV results
│   └── reports/           # Markdown reports
└── docs/
    └── METHODOLOGY.md     # Detailed methodology
```

## Parameters

All parameters are defined in `config.py`. They are **LOCKED after initial design** — do not tune parameters to improve results (that's curve-fitting).

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TICKER` | QQQ | Target instrument |
| `BENCHMARK` | SPY | RS(Z) benchmark |
| `GAP_DOWN_MIN` | -0.90% | Lower gap bound |
| `GAP_DOWN_MAX` | -0.70% | Upper gap bound |
| `RS_OVERSOLD_THRESHOLD` | -1.0 | RS(Z) filter |

## Interpreting Results

### Verdicts

| Verdict | Meaning |
|---------|---------|
| **TRADEABLE EDGE** | Statistically significant, robust across variants |
| **DEVELOPING** | Promising but needs more data or testing |
| **NO EDGE** | Results are not significant or robust |
| **INSUFFICIENT DATA** | Not enough events (N < 10) to conclude |

### Statistical Thresholds

- **p < 0.05**: Statistically significant
- **N ≥ 10**: Minimum sample for any conclusion
- **N ≥ 30**: Ideal sample for confidence

## Changing Tickers

To study a different instrument:

1. Edit `config.py`:
   ```python
   TICKER = "TSLA"  # New ticker
   ```

2. Re-run ALL scripts from step 1:
   ```bash
   python scripts/1_collect_data.py
   # ... continue through script 8
   ```

## Dependencies

```txt
yfinance>=0.2.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.7.0
seaborn>=0.12.0
requests>=2.28.0
```

**Alpaca API Keys Required:**
- Store your Alpaca paper trading API keys in `shared/config/keys/paper.env`
- Paper keys have full market data access via IEX feed
- Format:
  ```
  ALPACA_API_KEY=your_key_here
  ALPACA_API_SECRET=your_secret_here
  ```

## Data Sources

- **Daily OHLCV:** yfinance (Yahoo Finance API) — used for RS(Z) calculation
- **Intraday 5-min:** **Alpaca API** (full history) — **TSL3 slope is calculated here**
- Alpaca API keys required for intraday data (uses paper account keys from `shared/config/keys/paper.env`)

> **IMPORTANT:** TSL3 slope detection uses 5-minute bars ONLY. The daily TSL3 is calculated for reference but the confluence event detection specifically looks at the first 4 bars (9:30-9:50 AM) of the 5-minute chart to determine if slope is RISING at the open.

> **DATA SOURCE:** Alpaca provides full intraday history back to 2016. This overcomes yfinance's 60-day limitation for 5-minute data.

## Methodology

See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for detailed calculation explanations.

## Guardrails

1. **No parameter tuning after study launch**
2. **Minimum N = 10** for any conclusion
3. **Bonferroni correction** for multiple comparisons
4. **Confidence labels** on all results
5. **Baseline comparison** to show edge vs random

## License

Internal use only — Lakeem's QuantLab research.

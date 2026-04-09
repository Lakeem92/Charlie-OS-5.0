# How to Run This Study

**Study:** [Study Name]  
**Purpose:** [Brief description - e.g., "Analyze TSLA price action on earnings dates"]

---

## Prerequisites

1. **Activate Virtual Environment**
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

2. **Verify Dependencies**
   All required packages should already be installed. If not:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Check Data Sources**
   Consult [docs/API_MAP.md](../../docs/API_MAP.md) to confirm which data sources you'll use.

---

## Step 1: Collect Data

**Script:** `collect_data.py` or `get_[event]_dates.py`

**What it does:**
- Fetches event dates (earnings, conferences, FDA approvals, etc.)
- Outputs to: `[event]_dates.txt` or `[event]_dates.csv`

**Run:**
```powershell
python collect_data.py
```

**Expected Output:**
```
Fetching [event] dates from [source]...
Found 23 events between 2019-01-01 and 2024-12-31
Saved to: event_dates.txt
```

**Troubleshooting:**
- **"Connection timeout"** → Check internet, website may be down
- **"No data found"** → Verify date range, check if source URL changed
- **"Rate limit"** → Add `time.sleep(2)` between requests

---

## Step 2: Analyze Price Action

**Script:** `analyze_[ticker]_[event].py`

**What it does:**
- Loads event dates from Step 1
- Fetches OHLCV data from yfinance (or configured source)
- Calculates gaps, continuation, forward returns, volume spikes
- Generates summary statistics
- Outputs CSV and TXT reports

**Run:**
```powershell
python analyze_[ticker]_[event].py
```

**Expected Output:**
```
Analyzing [ticker] price action on [event] dates...
Loaded 23 events
Fetching OHLCV data from yfinance...
Retrieved 252 trading days
Calculating metrics...
  - Gap analysis: 23 events (12 up, 9 down, 2 flat)
  - Forward returns: 23 complete sequences
  - Volume spikes: 18 above 2x avg volume

Summary Statistics:
  Avg Gap %: +1.23%
  Avg Day 1 Return: -0.45%
  Avg Day 3 Return: -1.67%
  Win Rate (fade setup): 65.2%

Saved outputs:
  ✅ outputs/[study]_analysis.csv
  ✅ outputs/[study]_analysis.txt
```

**Troubleshooting:**
- **"yfinance timeout"** → Add retry logic or switch to Tiingo (see API_MAP.md)
- **"Insufficient data"** → Extend date range or check ticker symbol
- **"API key missing"** → Check `.env` file for required credentials

---

## Step 3: Review Results

### Output Files Location
All outputs are saved to: `outputs/`

### Files Generated

1. **outputs/[study]_analysis.csv**
   - Open in Excel or Google Sheets
   - Columns: Date, Ticker, Event, Gap%, Continuation%, Forward Returns, Volume
   - Sort by Gap% or Day3_Return to find extremes

2. **outputs/[study]_analysis.txt**
   - Human-readable summary
   - Trade-by-trade breakdown
   - Summary statistics (mean, median, win rate)

3. **README.md** (if generated)
   - Comprehensive analysis document
   - Trading strategies with entry/exit rules
   - Risk management lessons

### How to Interpret

**Look for:**
- **Win Rate:** What % of setups were profitable?
- **Average Return:** Mean return across all events
- **Consistency:** Do most events show the pattern, or just a few outliers?
- **Sample Size:** Need 15-20+ events for statistical confidence

**Example Interpretation:**
```
Study: TSLA Earnings Gap Analysis
Sample Size: 23 events (good)
Avg Gap: +1.2% (slight bullish bias)
Avg Day 3 Return: -1.67% (bearish edge!)
Win Rate (fade >2% gap ups): 8/10 = 80% (STRONG edge)

→ Strategy: Fade TSLA gap ups >2% on earnings
→ Entry: Open after earnings, Stop: +1.5%, Target: -2% by Day 3
```

---

## Step 4: Document Findings

Update or create `README.md` in this study folder with:

1. **Executive Summary**
   - Key finding in 2-3 sentences
   - E.g., "TSLA gaps up >2% on earnings but fades -1.67% by Day 3. Win rate: 80%."

2. **Detailed Analysis**
   - Tables, statistics, charts
   - Context for each metric

3. **Actionable Strategies**
   - Entry rules (when to enter)
   - Exit rules (stop loss, target)
   - Position sizing (% of portfolio)
   - Risk parameters (max loss per trade)

4. **Risk Management**
   - What can go wrong?
   - When does the pattern break?
   - How to adapt if market regime changes?

---

## Running Variations

### Test with VIX Filter
Add regime filter to see if pattern works better in high/low volatility:

```powershell
python analyze_[ticker]_[event].py --vix-filter 20
```

This will split results into VIX < 20 and VIX ≥ 20 buckets.

### Test with Volume Filter
Require minimum volume spike to validate pattern:

```powershell
python analyze_[ticker]_[event].py --min-volume-spike 2.0
```

Only includes events where volume ≥ 2x the 20-day average.

### Export Charts (if supported)
Generate visual charts of forward returns:

```powershell
python analyze_[ticker]_[event].py --charts
```

Outputs: `outputs/charts/forward_returns.png`, `outputs/charts/gap_distribution.png`

---

## Common Issues

### Issue: "Module not found: yfinance"
**Solution:**
```powershell
pip install yfinance
```

### Issue: "No data for [ticker]"
**Possible Causes:**
- Ticker symbol incorrect (check Yahoo Finance for correct symbol)
- Date range too narrow (extend start/end dates)
- Ticker delisted or merged (use historical symbol)

**Solution:**
```powershell
# Test ticker directly
python -c "import yfinance as yf; print(yf.download('TSLA', '2024-01-01', '2024-12-31'))"
```

### Issue: "API rate limit exceeded"
**Solution:**
- Add delays: `time.sleep(2)` between requests
- Cache results: Save to CSV and reuse
- Switch to fallback source (see [docs/API_MAP.md](../../docs/API_MAP.md))

---

## Clean Up

To remove outputs and start fresh:

```powershell
# Remove all output files
Remove-Item outputs/*.csv, outputs/*.txt

# Keep directory structure
```

---

## Where Outputs Go

```
studies/[study_name]/
├── collect_data.py              # Step 1 script
├── analyze_[ticker]_[event].py  # Step 2 script
├── study_notes.md               # Research notes
├── run_study.md                 # This file
├── README.md                    # Final analysis (create after run)
└── outputs/                     # All generated files
    ├── [study]_analysis.csv
    ├── [study]_analysis.txt
    └── charts/ (optional)
        ├── forward_returns.png
        └── gap_distribution.png
```

---

## Next Steps After Completion

1. **Archive Study**
   - Zip entire folder: `studies/[study_name]/`
   - Move to archive if pattern no longer works

2. **Share Results**
   - README.md is self-contained
   - Can share just that file + CSV for review

3. **Apply to Live Trading**
   - Use Alpaca paper trading to test strategy
   - See `shared/config/api_clients.py` → `AlpacaClient`

4. **Extend Study**
   - Add more events (extend date range)
   - Test on related tickers
   - Add additional filters (VIX, sector strength, etc.)

---

**Template Version:** 1.0  
**Last Updated:** December 14, 2025

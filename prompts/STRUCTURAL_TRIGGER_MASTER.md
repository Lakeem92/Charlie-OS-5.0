# Structural Trigger Master Protocol

**Purpose:** This document defines the canonical rules for structural trigger studies in the QuantLab Data_Lab.

**What Are Structural Triggers:** Events defined by technical conditions (e.g., TTM Squeeze + MACD alignment + PDH break), not news catalysts. Each historical occurrence of the trigger becomes a data point for statistical analysis.

**Scope:** All studies measuring condition-based setups, pattern recognition, and technical trigger events must follow this protocol.

---

## Canonical Data Rule

**Intraday structural trigger studies must use Alpaca intraday bars unless explicitly overridden by [docs/API_MAP.md](../docs/API_MAP.md).**

- Use `timeframe='5Min'`, `'15Min'`, or `'1Hour'` as appropriate for the trigger definition
- Daily structural triggers should also use Alpaca `timeframe='1Day'` per [prompts/VOLATILITY_LAB_MASTER.md](VOLATILITY_LAB_MASTER.md)
- Ensures consistent trigger identification across all studies

---

## Session and Timezone Defaults

**User Timezone:** America/Chicago (Central Time)

**Default Session:** Premarket + RTH (3:00 AM - 3:00 PM CT)

### Market Hours (Central Time):

- **Premarket Window:** 3:00 AM - 8:30 AM CT
- **RTH (Regular Trading Hours):** 8:30 AM - 3:00 PM CT (market open to close)
- **Extended Hours:** 3:00 PM - 7:00 PM CT (after-hours, rarely used)

### Timezone Conversion:

- Market data from Alpaca and other sources is typically returned in **Eastern Time (ET)**
- **All time-of-day statistics** (HOD timing, LOD timing, trigger time) must be converted to **Central Time (CT)** before analysis
- Example: If Alpaca returns HOD at `11:45 AM ET`, convert to `10:45 AM CT` for reporting

**Critical:** When answering questions like "HOD before noon?", use **noon CT (12:00 PM CT)**, not ET.

### Session Window Examples:

- `premarket+RTH` (default): 3:00 AM - 3:00 PM CT
- `RTH only`: 8:30 AM - 3:00 PM CT
- `premarket only`: 3:00 AM - 8:30 AM CT
- `full session`: 3:00 AM - 7:00 PM CT (premarket + RTH + extended hours)

---

## Trigger Definition Format

When requesting a structural trigger study, the user should provide:

### Required Parameters:

1. **Ticker(s):** Symbol or list of symbols to analyze (e.g., `TSLA`, `['BABA', 'JD', 'PDD']`)

2. **Timeframe:** Intraday resolution for trigger detection (e.g., `5m`, `15m`, `1h`)

3. **Session Window:** Trading hours to scan for triggers
   - **Default:** `premarket+RTH` (3:00 AM - 3:00 PM CT)
   - Examples: `RTH only` (8:30 AM - 3:00 PM CT), `premarket only` (3:00 AM - 8:30 AM CT), `full session` (3:00 AM - 7:00 PM CT)
   - All times in Central Time (CT) per Session Defaults

4. **Trigger Conditions:** Explicit boolean rules that must be TRUE simultaneously
   - Example: `TTM Squeeze = ON AND MACD > Signal AND Price > 20 SMA`
   - All conditions are AND-combined unless explicitly stated

5. **Confirmation Conditions:** Event that confirms trigger is actionable (optional)
   - Example: `Break PDH (Previous Day High)` or `Volume > 2x 10-bar avg`

6. **Measurement Window:** How long to track performance after trigger
   - Examples: `next 15m`, `next 30m`, `next 1h`, `EOD` (end of day)
   - Can specify multiple windows (e.g., `15m, 30m, 1h, EOD`)

7. **Output Metrics Required:** Which statistics to calculate (see Required Outputs section)

### Optional Parameters:

- **Lookback Period:** How far back in history to scan (default: 1 year)
- **Minimum Occurrences:** Minimum sample size to consider trigger valid (default: 20)
- **Direction Filter:** Long-only, short-only, or both (default: both)

### Example Trigger Definition:

```
Ticker: TSLA
Timeframe: 5m
Session Window: premarket+RTH (default, 3:00 AM - 3:00 PM CT)
Trigger Conditions:
  - TTM Squeeze = ON (at least 10 bars)
  - Squeeze releases (BB exits KC)
  - MACD crosses above Signal
  - Price > 20 SMA
Confirmation: Break PDH on release bar
Measurement Windows: 15m, 30m, 1h, EOD
Outputs: Win rate, MFE/MAE, HOD timing, volatility expansion
```

---

## TTM Squeeze (Lab Definition)

### Conceptual Definition:

The **TTM Squeeze** indicates a period of low volatility followed by expansion, identified when:

- **Squeeze ON:** Bollinger Bands contract inside Keltner Channels
  - BB upper band < KC upper band AND BB lower band > KC lower band
  
- **Squeeze Release:** First bar where Bollinger Bands exit Keltner Channels
  - BB upper band > KC upper band OR BB lower band < KC lower band

### Canonical Parameters (Lab Standard):

- **Bollinger Bands:** 20-period SMA, 2.0 standard deviations
- **Keltner Channels:** 20-period EMA, 1.5 x ATR(20)
- **ATR Period:** 20 bars (same as BB/KC basis)

### Implementation Note:

If we don't have an official ThinkOrSwim (TOS) calculation available, implement the standard canonical version defined above and document it. **Prefer consistency over "perfect match."**

All studies using TTM Squeeze must use these exact parameters unless explicitly overridden by the user. This ensures squeeze detection is comparable across all structural trigger studies.

### Code Reference:

```python
# Canonical TTM Squeeze implementation
def calculate_squeeze(df, bb_period=20, bb_std=2.0, kc_period=20, kc_atr_mult=1.5):
    # Bollinger Bands
    bb_basis = df['Close'].rolling(bb_period).mean()
    bb_std_dev = df['Close'].rolling(bb_period).std()
    bb_upper = bb_basis + (bb_std * bb_std_dev)
    bb_lower = bb_basis - (bb_std * bb_std_dev)
    
    # Keltner Channels
    kc_basis = df['Close'].ewm(span=kc_period).mean()
    atr = calculate_atr(df, kc_period)
    kc_upper = kc_basis + (kc_atr_mult * atr)
    kc_lower = kc_basis - (kc_atr_mult * atr)
    
    # Squeeze ON when BB inside KC
    squeeze_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    
    return squeeze_on
```

---

## Required Outputs for Structural Studies

All structural trigger studies must produce the following metrics:

### 1. Occurrence Count (Sample Size)
- Total trigger occurrences in lookback period
- Minimum sample size: 20 (warn if below threshold)
- Example: "Trigger occurred 47 times in 12 months"

### 2. Win Rate by Horizon
- Percentage of profitable occurrences for each measurement window
- Report for all specified windows (15m, 30m, 1h, EOD)
- Example: "Win rate: 15m=64%, 30m=58%, 1h=55%, EOD=51%"

### 3. MFE/MAE Distributions
- **MFE (Maximum Favorable Excursion):** Peak profit within measurement window
- **MAE (Maximum Adverse Excursion):** Worst drawdown within measurement window
- Report: mean, median, 25th/75th percentile
- Example: "Avg MFE: +1.2%, Avg MAE: -0.6%"

### 4. HOD/LOD Timing Distribution
- **HOD (High of Day):** Time when intraday peak occurred (% before 12pm, % after 12pm)
- **LOD (Low of Day):** Time when intraday low occurred
- Example: "67% of HOD occurred before 12:00 PM ET"

### 5. Volatility Expansion After Trigger
- Intraday True Range (TR) or ATR proxy after trigger fires
- Compare to baseline: "TR after trigger = 1.5x average TR"
- Confirms trigger precedes meaningful price movement

### 6. Failure Modes
- What happens when trigger fails?
- Common characteristics of failed setups
- Example: "Failed setups had 2x higher volume on reversal bar"

### Output Format:

Save all outputs in the study folder:
- `trigger_summary.txt` - High-level statistics
- `trigger_occurrences.csv` - All trigger dates/times with results
- `mfe_mae_distribution.csv` - MFE/MAE for each occurrence
- `timing_analysis.csv` - HOD/LOD timing data
- `failure_analysis.txt` - Failure mode patterns

---

## Agent Behavior

### 1. Default to Sensible Values
- **Don't ask for missing parameters** unless absolutely necessary
- Use defaults and clearly state them in output
- Example: "Using default session window: RTH only (9:30 AM - 4:00 PM ET)"

### 2. Consistency Across Runs
- **Do not change definitions across runs** without explicit user request
- If user asks to "run the TSLA squeeze study again," use the same parameters as last time
- Document all parameters used in study output

### 3. Save Everything
- **All outputs go in the study folder** (e.g., `studies/tsla_squeeze_study/`)
- Include raw data (CSV), summary stats (TXT), and any charts generated
- Make studies reproducible: save parameters, code, data, results

### 4. Explicit Documentation
- State which data source was used (Alpaca by default)
- Document any deviations from canonical definitions
- Note any assumptions made (e.g., "Assumed direction=long only")

### 5. Handle Edge Cases
- If sample size < 20, warn user: "Low sample size (N=15), results may not be statistically significant"
- If trigger never occurred, report: "Trigger conditions not met in lookback period"
- If data unavailable, try fallback sources per API_MAP.md and document

---

## Structural Study Workflow

1. **Parse Trigger Definition:** Extract ticker, timeframe, conditions, windows
2. **Fetch Data:** Use Alpaca intraday bars for specified lookback period
3. **Identify Triggers:** Scan for all occurrences where conditions are TRUE
4. **Measure Performance:** Calculate returns, MFE, MAE, timing for each occurrence
5. **Aggregate Statistics:** Compute win rates, distributions, failure modes
6. **Output Results:** Save summary, CSV, and analysis to study folder
7. **Document:** Record all parameters, data sources, and assumptions

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025  
**Related Files:**
- [prompts/VOLATILITY_LAB_MASTER.md](VOLATILITY_LAB_MASTER.md) - Volatility and return calculation rules
- [docs/API_MAP.md](../docs/API_MAP.md) - Data routing guide
- [shared/data_router.py](../shared/data_router.py) - Programmatic data routing

---

*Note: This protocol ensures structural trigger studies are consistent, reproducible, and statistically valid.*

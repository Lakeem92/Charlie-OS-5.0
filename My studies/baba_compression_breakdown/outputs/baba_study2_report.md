# BABA Compression-Range Breakdown Study Report

**Study Type:** Compression-Range Breakdown Analysis  
**Execution Date:** 2025-12-14 17:44:51  
**Ticker:** BABA (NYSE)  
**Study Period:** 2016-01-01 to 2025-12-13  

---

## Study Design

### Objective

Analyze the follow-through behavior when BABA breaks down below a compressed trading range, comparing to baseline compression days without breakdown.

### Definitions

**Compression Window:**
- Lookback: 20 trading days ending at day t-1 (day before potential breakdown)
- `range_high` = max(High) over the 20-day window
- `range_low` = min(Low) over the 20-day window
- `compression_range_pct` = (range_high - range_low) / Close(t-1)

**Compression Qualification:**
- Day t is eligible if compression_range_pct is in the bottom 20th percentile globally
- Threshold: 11.77% (computed from entire sample)

**Breakdown Trigger:**
- Qualified compression day where Close(t) < range_low

**Baseline:**
- Qualified compression day where Close(t) >= range_low (no breakdown)

---

## Data Source & Configuration

- **Data Source:** Alpaca (IEX feed)
- **Timezone:** Central Time (CT)
- **Sessions:** Premarket (3:00-8:29 CT) + RTH (8:30-15:00 CT)
- **Intraday Timeframe:** 5Min bars
- **Forward Horizons:** +1, +2, +3, +5, +10, +20 trading days
- **Daily Bars Analyzed:** 1351

---

## Sample Sizes

- **Breakdown Events:** 16
- **Baseline Events:** 251
- **Intraday Coverage:** 16/16 (100.0%)

---

## Key Results

### A. Forward Returns: Breakdown vs Baseline


**+1 Day:**
- Breakdown: Mean=0.06%, Median=0.16%, Hit Rate=62.5%
- Baseline: Mean=0.11%, Median=-0.03%, Hit Rate=48.0%
- **Difference (BD - BL):** Mean=-0.05%, Median=0.20%

**+2 Day:**
- Breakdown: Mean=0.70%, Median=0.30%, Hit Rate=56.2%
- Baseline: Mean=0.06%, Median=-0.30%, Hit Rate=45.0%
- **Difference (BD - BL):** Mean=0.64%, Median=0.59%

**+3 Day:**
- Breakdown: Mean=1.31%, Median=1.69%, Hit Rate=62.5%
- Baseline: Mean=0.14%, Median=-0.58%, Hit Rate=44.8%
- **Difference (BD - BL):** Mean=1.17%, Median=2.27%

**+5 Day:**
- Breakdown: Mean=1.74%, Median=2.37%, Hit Rate=75.0%
- Baseline: Mean=0.38%, Median=-0.61%, Hit Rate=46.4%
- **Difference (BD - BL):** Mean=1.37%, Median=2.98%

**+10 Day:**
- Breakdown: Mean=3.51%, Median=5.00%, Hit Rate=81.2%
- Baseline: Mean=1.37%, Median=-0.50%, Hit Rate=48.0%
- **Difference (BD - BL):** Mean=2.14%, Median=5.49%

**+20 Day:**
- Breakdown: Mean=6.16%, Median=3.77%, Hit Rate=56.2%
- Baseline: Mean=4.28%, Median=0.46%, Hit Rate=51.2%
- **Difference (BD - BL):** Mean=1.88%, Median=3.31%

### B. Downside Skew (MAE vs MFE)

**+1 Day (Breakdown):** Median MAE=-1.03%, Median MFE=1.00%
**+2 Day (Breakdown):** Median MAE=-1.59%, Median MFE=1.78%
**+3 Day (Breakdown):** Median MAE=-1.93%, Median MFE=2.65%
**+5 Day (Breakdown):** Median MAE=-2.36%, Median MFE=4.98%
**+10 Day (Breakdown):** Median MAE=-2.36%, Median MFE=8.03%
**+20 Day (Breakdown):** Median MAE=-3.99%, Median MFE=11.10%

### C. Max Drawdown

**+1 Day:** Breakdown Median=0.00%, Baseline Median=-0.03%
**+2 Day:** Breakdown Median=0.00%, Baseline Median=-0.68%
**+3 Day:** Breakdown Median=-0.25%, Baseline Median=-1.25%
**+5 Day:** Breakdown Median=-0.82%, Baseline Median=-2.14%
**+10 Day:** Breakdown Median=-0.82%, Baseline Median=-3.27%
**+20 Day:** Breakdown Median=-2.47%, Baseline Median=-4.55%

### D. Range Expansion on Breakdown Day

- **Breakdown Days with Range Expansion:** 50.0%
- **Baseline Days with Range Expansion:** 28.3%
- **Expansion Threshold:** >= 1.25x median prior 20-day range

**Interpretation:** Breakdowns tend to occur with range expansion.

---

## Intraday Breakdown Behavior


- **Premarket Breakdown Rate:** 3.0/5 (60.0%) traded below range_low
- **RTH Breakdown Rate:** 16/16 (100.0%) traded below range_low
- **RTH Close vs Range Low:** Mean -1.90% relative to range_low
- **Largest 5-Min Moves:** Available in intraday CSV


---

## Interpretation & Key Insights


1. **Immediate Follow-Through (+1d):**
   - Breakdown median: 0.16%
   - Baseline median: -0.03%
   - Breakdowns do not underperform baseline immediately.

2. **Medium-Term Performance (+10d):**
   - Breakdown median: 5.00%
   - Baseline median: -0.50%
   - Breakdowns show relative strength over 10 days.

3. **Range Expansion:**
   - 50.0% of breakdowns occur with range expansion
   - Range expansion is not a reliable characteristic.

4. **Downside Skew:**
   - MAE typically exceeds MFE magnitude on breakdown days
   - Moderate downside risk.

---

## Limitations & Failure Modes

1. **Sample Size:** 16 breakdown events may not be sufficient for robust statistical inference
2. **Compression Definition:** Bottom 20th percentile is a global static threshold; market regimes change over time
3. **No Context Filters:** Does not account for trend, sector performance, or broader market conditions
4. **Survivorship:** BABA has been volatile due to regulatory/geopolitical factors that may not apply to other tickers
5. **Historical Period:** 2016-01-01 to 2025-12-13 includes multiple regime changes (COVID, China tech crackdown, etc.)
6. **Intraday Coverage:** Only 100.0% of events have intraday data

---

## Outputs

All outputs saved in `outputs/`:

1. `baba_compression_breakdowns_events.csv` — Breakdown events with forward metrics
2. `baba_compression_baseline_events.csv` — Baseline compression events with forward metrics
3. `baba_compression_intraday_breakdown_metrics_5m.csv` — Intraday 5-min metrics
4. `baba_breakdown_vs_baseline_forward_returns.png` — Forward return distributions
5. `baba_breakdown_mae_mfe.png` — MAE vs MFE scatter plots
6. `baba_breakdown_range_expansion_rate.png` — Range expansion comparison
7. `baba_breakdown_equity_curves_median.png` — Median return paths
8. `baba_study2_report.md` — This report

---

**Study Completed:** 2025-12-14 17:44:51

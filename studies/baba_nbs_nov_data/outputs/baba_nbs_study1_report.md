# BABA China NBS November Data Release Study Report

**Study Type:** Event Window Analysis (NEW canonical study type)  
**Execution Date:** 2025-12-14 17:36:45  
**Ticker:** BABA (NYSE)  
**Event:** China NBS November macro data releases  

---

## Data Source & Configuration

- **Data Source:** Alpaca (IEX feed)
- **Timezone:** Central Time (CT)
- **Sessions:**
  - Premarket: 3:00-8:29 AM CT
  - RTH: 8:30 AM-3:00 PM CT
- **Event Dates:**
  - 2020-12-15
  - 2021-12-15
  - 2022-12-15
  - 2023-12-15
  - 2024-12-18

- **Daily Window:** [-10, +10] trading days
- **Intraday Analysis:** Event day (t) and next day (t+1)
- **Intraday Timeframe:** 5Min
- **Forward Return Horizons:** +1, +2, +3, +5, +10 trading days

---

## Sample Size & Limitations

- **Number of Events:** 5
- **Total Daily Observations:** 105
- **Intraday Sessions Analyzed:** 10

**Limitations:**
- Small sample size (n=5) limits statistical power
- Results are descriptive, not predictive
- China macro data releases may have varying market impact year-to-year
- No control for concurrent market events or regime changes
- Alpaca IEX feed may have limited premarket coverage for earlier years

---

## Key Findings

### A. Forward Returns from Event Close

**+1 Day:**
- Mean: -0.06%
- Median: -0.80%
- Hit Rate (% positive): 40.0% (2/5)
- Range: [-1.71%, 2.59%]

**+2 Day:**
- Mean: 0.49%
- Median: 1.03%
- Hit Rate (% positive): 60.0% (3/5)
- Range: [-3.12%, 3.56%]

**+3 Day:**
- Mean: -1.50%
- Median: -1.25%
- Hit Rate (% positive): 20.0% (1/5)
- Range: [-6.10%, 1.84%]

**+5 Day:**
- Mean: 0.13%
- Median: 1.02%
- Hit Rate (% positive): 80.0% (4/5)
- Range: [-3.82%, 1.90%]

**+10 Day:**
- Mean: -0.63%
- Median: 0.42%
- Hit Rate (% positive): 80.0% (4/5)
- Range: [-6.56%, 2.06%]


### B. Event Day Behavior

- **Mean Gap:** 0.05%
- **Mean Intraday Return:** -1.74%
- **Mean Daily Range:** 4.04%


### C. Risk Metrics (10-day post-event window)

- **Mean Max Favorable Excursion (MFE):** 3.70%
- **Mean Max Adverse Excursion (MAE):** -6.83%
- **Mean Max Drawdown:** -5.41%


### D. Volatility Analysis

**Daily Range Comparison:**
- Mean Pre-Event Range (days -10 to -1): 2.71%
- Mean Event Day Range (day 0): 4.04%
- **Range Expansion:** +49.3%

**ATR(14) Comparison:**
- Mean Pre-Event ATR: $4.19
- Mean Event Day ATR: $4.13
- **ATR Expansion:** -1.6%

**Intraday Realized Volatility (Event Day, Annualized):**
- Premarket: 105.8%
- RTH: 30.7%
- Full Session: 41.2%


---

## Interpretation

This study provides a descriptive analysis of BABA's price and volatility behavior around China NBS November macro data releases. Key observations:

1. **Small Sample Limitation:** With only 5 events, individual outliers can heavily influence means and percentages.
2. **Volatility Context:** Compare daily range and ATR expansion to assess whether these releases systematically increase volatility.
3. **Forward Return Asymmetry:** Examine hit rates and mean returns to identify any directional bias following the event.
4. **Intraday Timing:** Session high/low timing and premarket vs RTH behavior can inform intraday positioning.

**No indicators were used** (except ATR as a volatility metric per constraints). All analysis is based on raw price/volatility metrics.

---

## Outputs

All outputs are saved in the `outputs/` directory:

1. `baba_nbs_event_window_daily.csv` — Daily OHLCV and metrics for each event window
2. `baba_nbs_forward_returns.csv` — Forward returns and risk metrics for each event
3. `baba_nbs_intraday_metrics.csv` — Intraday session metrics (premarket + RTH)
4. `baba_nbs_rel_day_mean_return.png` — Mean return by relative day chart
5. `baba_nbs_rel_day_mean_range.png` — Mean daily range by relative day chart
6. `baba_nbs_forward_return_distributions.png` — Forward return distributions
7. `baba_nbs_study1_report.md` — This report

---

**Study Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

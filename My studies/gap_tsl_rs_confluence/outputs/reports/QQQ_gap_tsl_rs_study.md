# Gap Bias + TSL3 + RS(Z) Confluence Study: QQQ

**Generated:** 2026-02-17 11:29
**Data Range:** 2023-01-01 to present

## Study Question

When **QQQ** gaps down **-0.9% to -0.7%** and the TSL3 indicator 
slope is **RISING** at the open, does QQQ tend to close higher or lower — 
especially when its daily RS(Z) vs SPY is **≤ -1.0** (oversold)?

## Key Findings

- **Events Found:** 1
- **Win Rate (close > open):** 100.0%
- **Mean Return:** 0.07%
- **Statistical Significance:** Cannot determine
- **vs Baseline:** 0.03% better than average day
- **Statistically Different from Random?** No

### Verdict: **INSUFFICIENT DATA**
_Only 1 events found. Need at least 10 for reliable conclusions._

## Primary Setup Results

| Date | Gap % | RS(Z) | Open | Close | Open→Close |
|------|-------|-------|------|-------|------------|
| 2023-08-11 | -0.71% | -1.62 | 360.56 | 360.80 | 0.07% |

## Statistical Summary

| Metric | Open→Close | T+1 | T+2 | T+3 | T+5 |
|--------|------------|-----|-----|-----|-----|
| N | 1 | 1 | 1 | 1 | 1 |
| Win Rate | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% |
| Mean Return | 0.1% | 1.1% | 0.0% | -1.0% | -2.2% |
| Median Return | 0.1% | 1.1% | 0.0% | -1.0% | -2.2% |
| t-statistic | N/A | N/A | N/A | N/A | N/A |
| p-value | N/A | N/A | N/A | N/A | N/A |

## Baseline Comparison

| Measure | Confluence Events | All Trading Days |
|---------|-------------------|------------------|
| N | 1 | 782 |
| Mean Return | 0.07% | 0.04% |
| Std Dev | N/A | 1.06% |

**t-statistic:** N/A
**p-value:** N/A
**Significantly different at 5%?** ❌ No

## Conditional Analysis

### By Gap Band

| Value | N | Win Rate | Mean Return |
|-------|---|----------|-------------|
| Primary | 1 | 100% | 0.07% |

### By Rs Class

| Value | N | Win Rate | Mean Return |
|-------|---|----------|-------------|
| Crushed | 1 | 100% | 0.07% |

### By Ts Zone

| Value | N | Win Rate | Mean Return |
|-------|---|----------|-------------|
| OS | 1 | 100% | 0.07% |

### By Day Of Week

| Value | N | Win Rate | Mean Return |
|-------|---|----------|-------------|
| Friday | 1 | 100% | 0.07% |


## Robustness Check

Tested **60** parameter combinations 
(gap bands × RS thresholds × slope states).

**RISING slope variants with N≥10:** 1
**Profitable (WR>50%):** 1 (100%)

**Best variant:** Tiny gap, RS≤-0.5, RISING
  - N=14, Win Rate=64%, Mean=0.30%

See heatmap: `charts\QQQ_robustness_heatmap.png`


## Confidence Assessment

- **Sample Size:** 1 events - ❌ Insufficient
- **Statistical Significance:** Cannot determine
- **Robustness:** ✅ Strong (>70% of variants profitable)

### VERDICT: INSUFFICIENT DATA
_Only 1 events found. Need at least 10 for reliable conclusions._

## Methodology

See `docs/METHODOLOGY.md` for full calculation details.

## Assumptions & Limitations

- TSL3 is a Python recreation; minor floating-point differences from ThinkorSwim are possible.
- Intraday data limited to ~60 days via yfinance; daily analysis has full history.
- RS(Z) uses prior day's close — no look-ahead bias.
- Gap classification uses open vs prior close — pre-market prints not considered.
- Multiple statistical tests inflate Type I error risk; interpret with caution.

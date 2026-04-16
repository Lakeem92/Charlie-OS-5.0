# TSLA Momentum Extreme Indicator – Honesty Test Results

## What Was Tested

This study evaluated whether the **Cap Finder Momentum Extreme indicator** (combining RSI, moving average distance, and volume spikes) provides meaningful behavioral separation in Tesla (TSLA) stock.

**Test Period:** Last 252 trading days (approximately 1 year)  
**Data Source:** Alpaca Markets (IEX feed)  
**Indicator Components:**
- RSI(14) thresholds: Oversold ≤30, Overbought ≥70
- Price distance from 50-period MA (±5%)
- Volume spike (≥1.2x average)

## The Simple Question

**Does the indicator identify bars that behave differently going forward?**

If "oversold extreme" bars consistently lead to better returns than average, the indicator has predictive value. If not, it's just noise.

---

## Results Summary

| Group | Bar Count | Avg 5-Day Return | Max Adverse Move (5d) |
|-------|-----------|------------------|----------------------|
| **Baseline** (Normal bars) | 235 | +0.63% | -5.93% |
| **Oversold Extreme** | 9 | **-7.59%** ⚠️ | -12.25% |
| **Overbought Extreme** | 3 | **+3.21%** ✓ | -0.96% |

---

## Key Findings

### 1. **Oversold Signals Were Not Buying Opportunities**
- When the indicator flagged "oversold extreme" conditions, TSLA averaged **-7.59%** over the next 5 days
- This is **8.2 percentage points worse** than baseline
- Maximum adverse excursion was also significantly worse (-12.25% vs -5.93%)

**Translation:** The indicator's "oversold" signals did NOT mark good entry points. They marked continued weakness.

### 2. **Overbought Signals Showed Momentum Continuation**
- When the indicator flagged "overbought extreme," TSLA averaged **+3.21%** over the next 5 days
- This is **2.6 percentage points better** than baseline
- Minimal drawdown risk (-0.96% max adverse)

**Translation:** The indicator's "overbought" signals marked strong momentum that continued, not reversals.

### 3. **The Indicator Does Show Behavioral Separation**
Yes, the indicator identifies bars that behave differently—but **not in the traditional contrarian sense**. It's a momentum indicator, not a reversal indicator.

---

## Actionable Insights

### ❌ **What NOT To Do**
- **Do not buy TSLA on "oversold extreme" signals expecting a bounce.** The data shows these signals marked continued selling pressure.
- **Do not fade "overbought extreme" signals.** Shorting or selling into strength would have been costly.

### ✓ **What This Data Suggests**
1. **Momentum Continuation Strategy:**
   - Overbought extremes may be valid entry signals for momentum-following strategies
   - Small sample size (n=3) requires caution—needs more data

2. **Risk Management on Oversold Signals:**
   - If holding TSLA when oversold extremes trigger, consider tightening stops
   - These signals marked elevated downside risk (-12% max adverse vs -6% baseline)

3. **Regime Context Matters:**
   - This 252-day period may have been a strong bull trend for TSLA
   - "Buy the dip" logic doesn't work in all regimes
   - The indicator may behave differently in range-bound or bear markets

### 🔍 **Next Steps for Further Research**
1. **Expand Sample Size:** Test over 2-3 years to capture different market regimes
2. **Regime Filtering:** Separate bull/bear/neutral regimes and test behavior in each
3. **Entry Timing:** Test if waiting 1-2 days after the signal improves outcomes
4. **Exit Rules:** The 5-day horizon is arbitrary—test 1d, 3d, 10d, 20d exits
5. **Other Tickers:** Does this pattern hold for other momentum stocks (NVDA, AMD, etc.)?

---

## Bottom Line

**The Cap Finder indicator works—but not as a contrarian reversal tool.**

In the tested period, TSLA's "oversold" extremes marked deteriorating conditions (sell signal), while "overbought" extremes marked sustained strength (buy signal). This is a **momentum indicator disguised as an RSI oversold/overbought signal**.

**For traditional mean-reversion strategies:** This indicator does NOT validate "buy low, sell high" in TSLA during this period.

**For momentum strategies:** The overbought signals showed promise, but the small sample (n=3) means this needs validation over a longer period.

---

## Data Integrity Notes

✓ Data sourced from Alpaca Markets (IEX feed) per governance rules  
✓ All 252 trading days validated  
✓ No survivorship bias (single ticker study)  
✓ Forward returns calculated from actual close prices  
✓ Max adverse excursion measured from intraday lows  

**Reproducibility:** Run `tsla_honesty_test.py` to regenerate these results at any time.

---

## Study Metadata

**Study Type:** honesty_test (indicator behavioral separation)  
**Execution Date:** December 14, 2025  
**Data Period:** ~December 2024 - December 2025  
**Indicator:** Trend Strength + NR7 + Momentum Extremes (Cap Finder)  
**Data Router:** Enforced Alpaca per governance (study_type='honesty_test')

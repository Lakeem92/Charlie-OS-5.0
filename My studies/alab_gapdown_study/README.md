# ALAB 10%+ Gap Down Study

## Overview
This study analyzes the performance of $ALAB following pre-market gap downs of 10% or more. The analysis examines day-of recovery patterns and forward returns over various time horizons (1-5 days and 10-20 days out).

**Study Period:** March 2024 - February 2026 (475 trading days analyzed)  
**Gap Down Events Identified:** 3 events meeting the ≥10% gap down criteria

---

## Key Findings

### 📉 Gap Down Characteristics
- **Average Gap Down:** -11.78%
- **Largest Gap Down:** -12.34% (February 3, 2025)
- **Smallest Gap Down:** -11.47% (August 5, 2024)
- **Gap Range:** Relatively tight clustering around -11% to -12%

### 🎯 Day-of Performance (Open to Close)
The day-of performance shows **mixed but slightly positive results**:
- **Mean Return:** +2.80%
- **Median Return:** +10.37%
- **Win Rate:** 66.7% (2 out of 3 events)
- **Best Recovery:** +16.68% (August 5, 2024)
- **Worst Performance:** -18.66% (January 27, 2025)

**Key Insight:** There's significant variance in day-of performance, suggesting that external factors (market conditions, news catalysts) heavily influence whether ALAB recovers or continues lower on the gap down day itself.

---

## Forward Returns Analysis

### 📈 Short-Term (Days 1-5)
The 1-5 day forward period shows **consistently positive returns**:

| Day | Mean Return | Median Return | Win Rate |
|-----|-------------|---------------|----------|
| 1   | +2.83%      | +3.68%        | 66.7%    |
| 2   | +0.14%      | +8.61%        | 66.7%    |
| 3   | +5.56%      | +6.51%        | 66.7%    |
| 4   | +6.21%      | +3.23%        | 66.7%    |
| 5   | +4.67%      | +5.27%        | 66.7%    |

**Key Findings:**
- **Strong bounce-back tendency:** All days show positive mean returns
- **Best performance window:** Days 3-4 appear to be the sweet spot with mean returns above 5%
- **Consistent win rate:** 66.7% probability of positive returns across all short-term periods
- **Day 2 anomaly:** Despite low mean return (+0.14%), the median is +8.61%, indicating one outlier dragged down the average

**Trading Implication:** The 1-5 day window presents a favorable risk/reward profile for mean reversion plays following 10%+ gaps down.

---

### 📊 Medium-Term (Days 10-20)
The 10-20 day forward period reveals a **notable deterioration**:

| Day | Mean Return | Median Return | Win Rate |
|-----|-------------|---------------|----------|
| 10  | +4.37%      | -4.94%        | 33.3%    |
| 15  | -3.46%      | -1.78%        | 33.3%    |
| 20  | -15.41%     | -10.67%       | 0.0%     |

**Critical Findings:**
- **Sharp reversal:** Returns turn decisively negative by day 15-20
- **Win rate collapse:** Drops from 66.7% (days 1-5) to 0% by day 20
- **Day 20 disaster:** Mean return of -15.41% with 0% win rate suggests the initial gap down signals deeper structural issues
- **Momentum shift:** The positive divergence between mean and median on day 10 is the first warning sign that the bounce is losing steam

**Trading Implication:** Exit bounces by day 5-7. Holding past 10 days appears to be a losing strategy based on this dataset.

---

## Individual Event Analysis

### Event 1: August 5, 2024 (Gap: -11.47%)
- **Day 0:** +16.68% ✅ Strong recovery
- **Days 1-5:** Negative returns (gave back the bounce)
- **Days 10-20:** Consistently negative, ending at -10.67% by day 20
- **Pattern:** Classic "dead cat bounce" - strong intraday recovery followed by sustained weakness

### Event 2: January 27, 2025 (Gap: -11.52%)
- **Day 0:** -18.66% ❌ Catastrophic follow-through
- **Days 1-5:** Strong bounce (+8-22% from the close)
- **Days 10-20:** Peaked at +24% on day 10, then faded to -6.5% by day 20
- **Pattern:** Failed breakdown → relief rally → eventual failure

### Event 3: February 3, 2025 (Gap: -12.34%, largest gap)
- **Day 0:** +10.37% ✅ Solid recovery
- **Days 1-5:** Strong continued momentum (+3-18% from the close)
- **Days 10-20:** Massive collapse to -29% by day 20 ❌
- **Pattern:** Initial strength followed by complete breakdown
- **Note:** This is the most recent event and may be influenced by ongoing price action

---

## Statistical Summary

### Success Metrics
- **Best performer (Day 5):** January 27, 2025 event with +17.99% 5-day forward return
- **Most consistent bounce:** Days 3-4 with 66.7% win rate and 5-6% average returns
- **Safest entry:** Day 1 after the gap (avoid catching the falling knife on day 0)

### Risk Metrics
- **Highest day-of risk:** 33% chance of -18% or worse continuation on the gap day itself
- **Medium-term danger zone:** Days 15-20 show systematic underperformance
- **Maximum observed drawdown:** -29% by day 20 (February 3 event)

---

## Trading Strategy Recommendations

### ✅ FAVORABLE SETUP (Mean Reversion Play)
1. **Wait for confirmation:** Enter on day 1 after observing day-0 behavior
2. **Target window:** Days 3-4 for optimal risk/reward
3. **Stop loss:** Below the gap-down low or -5% from entry
4. **Exit strategy:** Take profits by day 5 at the latest; ideally day 3-4

### ⚠️ HIGH RISK / AVOID
1. **Day-0 knife catching:** Too much volatility and 33% chance of severe follow-through
2. **Holding beyond day 10:** Returns turn negative and deteriorate rapidly
3. **Assuming gaps fill:** None of the events show sustainable rallies back to pre-gap levels within 20 days

### 🔍 Additional Considerations
- **Sample size limitation:** Only 3 events; statistical significance is limited
- **Market context matters:** Each event occurred in different market conditions
- **Company-specific risks:** ALAB appears to have fundamental issues given the sustained post-gap weakness
- **Volatility decay:** The initial bounce energy dissipates quickly; momentum traders should exit early

---

## Conclusion

**Main Takeaway:** ALAB exhibits a reliable short-term bounce pattern after 10%+ gap downs (days 1-5), but this is followed by a systematic deterioration in returns by days 10-20. This suggests that while mean reversion traders can profit from the initial oversold relief rally, the gap downs likely signal genuine fundamental deterioration rather than temporary technical weakness.

**Recommended Approach:** 
- **For swing traders:** Play the 1-5 day bounce with tight stops and defined exits
- **For position traders:** AVOID holding through gap downs - the 20-day performance is catastrophic
- **For contrarians:** This is NOT a buy-and-hold opportunity post-gap; it's a trade-in-and-out situation

**Risk Warning:** The small sample size (n=3) means these patterns could shift with additional data. Always use proper position sizing and risk management.

---

## Files Generated
- `outputs/alab_gapdown_events.csv` - Detailed event data with all forward returns
- `outputs/alab_gapdown_summary.txt` - Statistical summary of findings
- `run_alab_gapdown_study.py` - Python script to reproduce the analysis

## Methodology
- **Data Source:** Yahoo Finance (yfinance)
- **Gap Calculation:** (Open - Previous Close) / Previous Close × 100
- **Gap Threshold:** ≤ -10.0%
- **Return Calculation:** All forward returns calculated from day-of close price
- **Day 0 Return:** Calculated as (Close - Open) / Open × 100

---

*Study completed: February 11, 2026*

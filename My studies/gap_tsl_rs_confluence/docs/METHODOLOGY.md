# Methodology: Gap Bias + TSL3 + RS(Z) Confluence Study

## Overview

This document details the exact calculations and methodology used in the confluence study. The goal is full reproducibility — any analyst should be able to verify these calculations independently.

---

## 1. TSL3 Indicator Recreation

The TSL3 (TrendStrength Line v4.5) indicator is recreated in Python to match the ThinkorSwim implementation. This is a **consensus trend indicator** that combines three normalized momentum methods.

### 1.1 Calculation Pipeline

#### Step 1: ATR Calculation
Calculate the 14-period **Exponential** Average True Range:

```
True Range = max(High - Low, |High - Close[1]|, |Low - Close[1]|)
ATR = EMA(True Range, 14)
```

> Note: Use exponential smoothing (EMA), not simple moving average.

#### Step 2: Three Raw Methods

**A. Price Change (PC)**
```
raw_pc = (Close - Close[20]) / ATR
```
Measures how much price has changed over 20 bars, normalized by volatility.

**B. EMA Slope**
```
ema21 = EMA(Close, 21)
ema_slope_raw = (ema21 - ema21[1]) / ATR
raw_ema_slope = SMA(ema_slope_raw, 5)
```
Measures the smoothed slope of the 21-bar EMA.

**C. MA Distance**
```
ema20 = EMA(Close, 20)
sma50 = SMA(Close, 50)
raw_ma_dist = (ema20 - sma50) / ATR
```
Measures the distance between fast and slow moving averages.

#### Step 3: Z-Score Normalization

For each raw method, normalize to a [-1, +1] scale:

```
roll_mean = rolling_mean(raw_value, 100)
roll_std = rolling_std(raw_value, 100)
z = (raw_value - roll_mean) / roll_std
z_clamped = clip(z, -2.5, +2.5)
normalized = clip(z_clamped / 2.0, -1, +1)
```

This produces `norm_pc`, `norm_ema`, `norm_ma`.

#### Step 4: Consensus
```
consensus = mean(norm_pc, norm_ema, norm_ma)
```

#### Step 5: TrendScore
```
trend_score = consensus × 100
```
Range: -100 to +100

#### Step 6: Signal Line
```
signal_line = EMA(trend_score, 9)
```

#### Step 7: Slope Calculation
```
raw_slope = (trend_score - trend_score[5]) / 5
slope = EMA(raw_slope, 3)

slope_state:
  RISING (+1)   if slope > 0.25
  DROPPING (-1) if slope < -0.25
  NEUTRAL (0)   otherwise
```

#### Step 8: Momentum & Acceleration
```
momentum = trend_score - trend_score[1]
acceleration = momentum - momentum[1]
```

#### Step 9: Zone Classification
```
ts_zone:
  "OB"   (Overbought)  if trend_score ≥ 70
  "BULL"               if 30 ≤ trend_score < 70
  "NEUT"               if -30 < trend_score < 30
  "BEAR"               if -70 < trend_score ≤ -30
  "OS"   (Oversold)    if trend_score ≤ -70
```

### 1.2 Parameter Values

| Parameter | Value | Description |
|-----------|-------|-------------|
| TSL_PC_LOOKBACK | 20 | Price change lookback |
| TSL_EMA_LEN | 21 | EMA length for slope method |
| TSL_EMA_SLOPE_SMOOTH | 5 | Smoothing for EMA slope |
| TSL_MA1_LEN | 20 | Fast MA (EMA) length |
| TSL_MA2_LEN | 50 | Slow MA (SMA) length |
| TSL_ATR_LEN | 14 | ATR period |
| TSL_NORM_LEN | 100 | Z-score normalization window |
| TSL_Z_CLAMP | 2.5 | Maximum Z-score before clamping |
| TSL_Z_TO_UNIT | 2.0 | Divisor to scale Z to [-1, +1] |
| TSL_SIGNAL_LEN | 9 | Signal line EMA length |
| TSL_SLOPE_LEN | 5 | Bars for slope calculation |
| TSL_SLOPE_SMOOTH | 3 | EMA smoothing on slope |
| TSL_SLOPE_NEUTRAL_THRESHOLD | 0.25 | Threshold for RISING/DROPPING |

These values **exactly match** the ThinkorSwim TrendStrengthNR7 v4.5 indicator defaults.

### 1.3 Warmup Period

The first ~100 bars (TSL_NORM_LEN) have incomplete Z-score normalization and are marked as "warmup" period. These should not be used in analysis.

---

## 2. RS(Z) Calculation

Relative Strength Z-score measures how the ticker is performing versus a benchmark (typically SPY), normalized to a statistical scale.

### 2.1 Calculation Steps

```
# Rolling momentum (20-day returns)
ticker_mom = (ticker_close - ticker_close[20]) / ticker_close[20]
bench_mom = (bench_close - bench_close[20]) / bench_close[20]

# Raw relative strength
rs_raw = ticker_mom - bench_mom

# Z-score normalization
rs_mean = rolling_mean(rs_raw, 60)
rs_std = rolling_std(rs_raw, 60)
rs_z = (rs_raw - rs_mean) / rs_std
```

### 2.2 Classification

| RS(Z) Value | Classification |
|-------------|----------------|
| ≤ -1.0 | Crushed |
| -1.0 to -0.5 | Weak |
| -0.5 to 0.5 | Neutral |
| 0.5 to 1.0 | Strong |
| > 1.0 | Dominant |

### 2.3 Rationale

- **20-day momentum** captures intermediate-term trend
- **60-day Z-score window** provides stable normalization
- **Z-score** makes comparisons across different volatility regimes possible
- **-1.0 threshold** approximates ~16th percentile (1 std below mean)

---

## 3. Gap Classification

### 3.1 Gap Calculation

```
gap_pct = (Open - Close[previous day]) / Close[previous day] × 100
```

Note: Uses the **prior day's close**, not the prior candle's close on intraday charts.

### 3.2 Gap Bands

| Band | Range | Description |
|------|-------|-------------|
| Tiny | -0.50% to -0.30% | Minimal gap |
| Small | -0.70% to -0.50% | Minor gap |
| Primary | -0.90% to -0.70% | Study focus gap |
| Large | -1.50% to -0.90% | Significant gap |
| Crash | -3.00% to -1.50% | Major gap down |

### 3.3 Why These Ranges?

- **Primary band (-0.90% to -0.70%)**: Large enough to represent "selling pressure" but not extreme
- **Robustness bands**: Test whether edge persists across different gap sizes
- **No look-ahead**: Gap is observable at market open

---

## 4. Confluence Detection

### 4.1 Three-Condition Logic

A **confluence event** requires ALL THREE conditions:

1. **Gap Down** in specified range (default: -0.90% to -0.70%)
2. **TSL3 Slope = RISING on 5-minute chart** at market open (any of first 4 bars, 9:30-9:50 AM)
3. **RS(Z) ≤ threshold** on prior day's close (default: ≤ -1.0)

> **CRITICAL:** The TSL3 slope condition is evaluated on the **5-minute intraday chart**, NOT the daily chart. This captures the real-time momentum state at the market open.

### 4.2 Timing Details

| Condition | Timing | Timeframe | Why |
|-----------|--------|-----------|-----|
| Gap | Open vs Prior Close | Daily | Observable at market open |
| TSL Slope | First 4 bars of RTH | **5-minute** | Real-time intraday signal |
| RS(Z) | Prior day's close | Daily | Known before gap opens |

> **Note:** TSL3 is calculated on BOTH daily and 5-minute timeframes, but only the **5-minute TSL3 slope** is used for confluence detection. The daily TSL3 provides context (prior day's TrendScore zone) but is not part of the primary trigger.

### 4.3 No Look-Ahead Bias

- RS(Z) uses **prior day's** closing values (you'd know this before the gap)
- Gap is measured at **market open** (observable in real-time)
- Slope state is assessed from **first 20 minutes** of RTH

---

## 5. Statistical Tests

### 5.1 One-Sample t-Test

Tests whether mean return is significantly different from zero:

```
H₀: μ = 0 (no edge)
H₁: μ ≠ 0 (edge exists)

t = (x̄ - 0) / (s / √n)
```

Interpretation:
- **p < 0.01**: Highly significant
- **p < 0.05**: Significant
- **p < 0.10**: Marginally significant
- **p ≥ 0.10**: Not significant

### 5.2 Two-Sample t-Test

Compares confluence returns to all-day returns:

```
H₀: μ_confluence = μ_baseline
H₁: μ_confluence ≠ μ_baseline
```

Uses Welch's t-test (unequal variances assumed).

### 5.3 Multiple Comparison Warning

With 60 variant combinations tested (5 gaps × 4 RS thresholds × 3 slopes):
- **Bonferroni correction**: α_corrected = 0.05 / 60 = 0.00083
- Variants must achieve **p < 0.00083** to claim significance after correction
- Alternative: Report FDR-adjusted p-values

---

## 6. Guardrails

### 6.1 No Parameter Tuning

**Parameters are locked at study inception.** Do not:
- Adjust gap ranges to improve results
- Tweak RS thresholds after seeing data
- Cherry-pick "best" slope conditions

This prevents curve-fitting and ensures out-of-sample validity.

### 6.2 Minimum Sample Size

| N | Confidence Level |
|---|-----------------|
| < 10 | Cannot draw conclusions (LOW) |
| 10-29 | Preliminary indication (MEDIUM) |
| ≥ 30 | Reliable conclusion (HIGH) |

Results with N < 10 are flagged as "LOW CONFIDENCE" and excluded from trading decisions.

### 6.3 Robustness Requirement

An edge is only considered **robust** if:
- >50% of related variants show positive win rate
- Edge persists across multiple gap sizes
- Edge persists across multiple RS thresholds

Fragile edges (only significant in one configuration) are considered unreliable.

### 6.4 Baseline Comparison

Always compare to the baseline (all trading days) to demonstrate that the edge is **incremental** — not just positive returns in a bull market.

---

## 7. Data Quality Notes

### 7.1 yfinance Limitations

- **Daily data**: Full history available, reliable
- **Intraday data**: Limited to ~60 days; timezone handling required
- **Adjusted prices**: Uses adjusted close for daily; raw prices for intraday

### 7.2 Missing Data Handling

- Days without intraday data: Slope condition cannot be verified → excluded
- Gaps in daily data: Interpolation NOT used → excluded
- Weekend/holiday gaps: Treated normally (gap from Friday to Monday)

### 7.3 Timezone Handling

All intraday timestamps converted to **US/Eastern** (market time) with timezone info stripped for consistency.

---

## 8. Interpretation Guidelines

### 8.1 What a Positive Result Means

If win rate > 50% and p < 0.05:
> "Gap-down days with rising TSL slope and crushed RS(Z) tend to close higher than open more often than chance."

This suggests potential **mean-reversion** behavior under these conditions.

### 8.2 What It Does NOT Mean

- Guaranteed profits (trading costs, slippage not modeled)
- Future persistence (regime change risk)
- Applicability to other tickers (study is ticker-specific)

### 8.3 Red Flags

Be skeptical if:
- Very high win rate (>70%) with small N
- Only one variant is significant
- Edge disappears with Bonferroni correction
- Edge is inconsistent across similar gap sizes

---

## Appendix: TSL3 Python Implementation

See `scripts/2_calculate_tsl3.py` for the full Python implementation. Key function:

```python
def calculate_tsl3(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Calculate ATR (exponential)
    # 2. Calculate three raw methods (PC, EMA slope, MA distance)
    # 3. Z-score normalize each method
    # 4. Average for consensus
    # 5. Scale to TrendScore (-100 to +100)
    # 6. Calculate signal line, slope, momentum, acceleration
    # 7. Classify slope state and TS zone
    return df_with_tsl3_columns
```

---

*Document Version: 1.0*  
*Last Updated: 2026-02*

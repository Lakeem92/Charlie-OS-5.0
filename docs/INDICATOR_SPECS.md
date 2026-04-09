# Indicator Specifications

## Purpose

This document is the authoritative specification for all indicators used in QuantLab Data_Lab.

Only indicators defined here may be used in studies.

## Usage Rules

1. **Indicator definitions must reflect ThinkScript logic exactly**
   - Python implementations in `shared/indicators/` must match these specifications verbatim
   - No deviations or "improvements" without updating this specification first

2. **No parameter tuning or reinterpretation is allowed during execution**
   - Default parameters are canonical
   - Non-default parameters must be explicitly stated in study definitions

3. **Python implementations must follow these specs verbatim**
   - Output column names must match specification
   - Calculation order must match specification
   - Mathematical operations must match ThinkScript behavior

---

## Indicator: Trend Strength Candles v2 + NR7 + Momentum Extremes (Cap Finder)

### Source
ThinkScript (user-provided)
Reference: `prompts/thinkscript/TREND_STRENGTH_NR7_CAPFINDER.thinkscript`

### Timeframes
- Daily
- Intraday

### Required Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pcLookback` | int | 20 | Price change lookback period |
| `emaLen` | int | 21 | EMA length for slope calculation |
| `emaSlopeSmooth` | int | 5 | Smoothing period for EMA slope |
| `ma1Type` | string | "EMA" | First moving average type (EMA or SMA) |
| `ma1Len` | int | 20 | First moving average length |
| `ma2Type` | string | "SMA" | Second moving average type (SMA or EMA) |
| `ma2Len` | int | 50 | Second moving average length |
| `atrLen` | int | 14 | ATR length for normalization |
| `zscoreLookback` | int | 200 | Rolling z-score lookback period |

### Calculation Components

**Method 1: Price Change (ATR-normalized)**
```
rawPc = (close - close[pcLookback]) / ATR(atrLen)
pcZscore = zscore(rawPc, zscoreLookback)
```

**Method 2: EMA Slope (ATR-normalized, smoothed)**
```
emaSeries = EMA(close, emaLen)
raw_ema_slope = (emaSeries - emaSeries[1]) / ATR(atrLen)
raw_ema_slope_sm = SMA(raw_ema_slope, emaSlopeSmooth)
emaZscore = zscore(raw_ema_slope_sm, zscoreLookback)
```

**Method 3: MA Distance (ATR-normalized)**
```
ma1 = MA(close, ma1Len, ma1Type)
ma2 = MA(close, ma2Len, ma2Type)
rawMaDist = (ma1 - ma2) / ATR(atrLen)
maZscore = zscore(rawMaDist, zscoreLookback)
```

**Consensus Score**
```
consensusScore = (pcZscore + emaZscore + maZscore) / 3.0
```

**Agreement Factor**
```
agreement = abs(sign(pcZscore) + sign(emaZscore) + sign(maZscore)) / 3.0
Values: 0, 1/3, 2/3, 1
```

**Scaled and Clamped Consensus**
```
consensusScaled = consensusScore * 100.0
consensusClamped = clamp(consensusScaled, -100, 100)
```

**NR7 (Narrow Range 7)**
```
range = high - low
lowestPastRange = min(range[1] to range[6])
is_nr7 = (range < lowestPastRange)
```

### Core Outputs

| Output | Type | Range | Description |
|--------|------|-------|-------------|
| `atr` | float | > 0 | ATR value used for normalization |
| `rawPc` | float | unbounded | Raw price change (ATR-normalized) |
| `raw_ema_slope_sm` | float | unbounded | Smoothed EMA slope (ATR-normalized) |
| `rawMaDist` | float | unbounded | MA distance (ATR-normalized) |
| `pcZscore` | float | unbounded | Z-score of price change |
| `emaZscore` | float | unbounded | Z-score of EMA slope |
| `maZscore` | float | unbounded | Z-score of MA distance |
| `consensusScore` | float | unbounded | Average of three z-scores |
| `agreement` | float | 0–1 | Fraction of signals agreeing on direction |
| `consensusScaled` | float | unbounded | Consensus * 100 |
| `consensusClamped` | float | -100 to +100 | Clamped consensus score |
| `is_nr7` | boolean | true/false | Narrow range compression flag |
| `trend_state` | string | categorical | Bucket label (see below) |

### Signal Interpretations

| consensusClamped Range | Trend State | Interpretation |
|------------------------|-------------|----------------|
| ≥ 70 | MAX_CONVICTION_BULL | Highest bullish conviction |
| 50 to 69 | STRONG_BULL | Strong bullish trend |
| 30 to 49 | MILD_BULL | Moderate bullish trend |
| 10 to 29 | WEAK_BULL | Weak bullish trend |
| -9 to 10 | NEUTRAL | No directional bias |
| -29 to -10 | WEAK_BEAR | Weak bearish trend |
| -49 to -30 | MILD_BEAR | Moderate bearish trend |
| -69 to -50 | STRONG_BEAR | Strong bearish trend |
| ≤ -70 | MAX_CONVICTION_BEAR | Highest bearish conviction |

**NR7 Interpretation:**
- `is_nr7 = true` indicates volatility compression (potential expansion imminent)
- Used in combination with trend state for timing entries

### Momentum Extremes Override (Cap Finder)

The indicator adds momentum extreme detection to override gradient candle colors when extreme conditions are met.

**Additional Inputs:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enableMomentumExtremeOverride` | bool | true | Enable/disable momentum extreme override |
| `cap_rsiLength` | int | 14 | RSI calculation period |
| `cap_rsiOversold` | int | 30 | RSI oversold threshold |
| `cap_rsiOverbought` | int | 70 | RSI overbought threshold |
| `cap_maType` | string | "SMA" | Moving average type for price comparison |
| `cap_maLength` | int | 50 | Moving average length |
| `cap_percentageThreshold` | float | 5.0 | Distance from MA (%) for below/above flags |
| `cap_volumeMultiplier` | float | 1.2 | Volume spike multiplier threshold |
| `cap_volumeLength` | int | 20 | Volume average lookback |

**Cap Finder Calculations:**
```
capRsi = RSI(close, cap_rsiLength)  # Wilder's RSI
capMa = MovingAverage(cap_maType, close, cap_maLength)
capVolAvg = SMA(volume, cap_volumeLength)

capBelow = close < capMa * (1 - cap_percentageThreshold / 100)
capAbove = close > capMa * (1 + cap_percentageThreshold / 100)
capVolSpike = volume >= capVolAvg * cap_volumeMultiplier

oversoldExtreme = (capRsi <= cap_rsiOversold) AND capBelow AND capVolSpike
overboughtExtreme = (capRsi >= cap_rsiOverbought) AND capAbove AND capVolSpike
```

**Priority Logic:**
1. NR7 overrides all (WHITE candle)
2. If `enableMomentumExtremeOverride = true`:
   - `oversoldExtreme = true` → BLUE candle
   - `overboughtExtreme = true` → YELLOW candle
3. Otherwise: gradient color based on consensus

**Additional Outputs:**

| Output | Type | Range | Description |
|--------|------|-------|-------------|
| `cap_rsi` | float | 0-100 | RSI value (Wilder's smoothing) |
| `cap_ma` | float | > 0 | Moving average for price comparison |
| `cap_vol_avg` | float | > 0 | Average volume over cap_volumeLength |
| `cap_below` | boolean | true/false | Price is significantly below MA |
| `cap_above` | boolean | true/false | Price is significantly above MA |
| `cap_vol_spike` | boolean | true/false | Volume exceeds threshold |
| `oversoldExtreme` | boolean | true/false | All three oversold conditions met |
| `overboughtExtreme` | boolean | true/false | All three overbought conditions met |
| `momentum_extreme_state` | string | categorical | "OVERSOLD", "OVERBOUGHT", or "NONE" |

### Python Implementation
`shared/indicators/trend_strength_nr7.py`

Function: `compute_trend_strength_nr7(df, params=TrendStrengthParams())`

---

## Indicator: Advanced TTM Squeeze (Tight + Soft)

### Source
ThinkScript (user-provided)

### Timeframes
- Intraday only (5m, 15m recommended)

### Required Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `length` | int | 20 | Base period for SMA, KC, BB |
| `nK` | float | 1.5 | Keltner Channel ATR multiplier |
| `nBB_tight` | float | 2.0 | Bollinger Band std dev multiplier (tight) |
| `nBB_soft` | float | 1.7 | Bollinger Band std dev multiplier (soft) |

### Calculation Components

**Keltner Channels (KC)**
```
avg = SMA(close, length)
atr = SMA(TrueRange, length)  # SIMPLE ATR, not EMA
upper_kc = avg + nK * atr
lower_kc = avg - nK * atr
```

**Bollinger Bands (BB)**
```
avg = SMA(close, length)  # Same as KC basis
sd = StdDev(close, length)  # Population std dev (ddof=0)

upper_bb_tight = avg + nBB_tight * sd
lower_bb_tight = avg - nBB_tight * sd

upper_bb_soft = avg + nBB_soft * sd
lower_bb_soft = avg - nBB_soft * sd
```

**Squeeze Conditions**
```
squeeze_tight_on = (upper_bb_tight < upper_kc) AND (lower_bb_tight > lower_kc)
squeeze_soft_on = (upper_bb_soft < upper_kc) AND (lower_bb_soft > lower_kc)

# Tight dominates soft
squeeze_soft_on = squeeze_soft_on AND NOT squeeze_tight_on

squeeze_any_on = squeeze_tight_on OR squeeze_soft_on
squeeze_release = squeeze_any_on[-1] AND NOT squeeze_any_on
```

**Momentum**
```
value_a = 4 * close
sm1 = SMA(close, length)
sm2 = SMA(sm1, length)
sm3 = SMA(sm2, length)
sm4 = SMA(sm3, length)
momentum = value_a - sm4

momentum_sign = sign(momentum)  # +1, 0, -1
momentum_accel = momentum > momentum[1]  # boolean
```

### Core Outputs

| Output | Type | Description |
|--------|------|-------------|
| `kc_avg` | float | Keltner Channel basis (SMA) |
| `kc_atr` | float | Simple ATR value |
| `upper_kc` | float | Upper Keltner Channel band |
| `lower_kc` | float | Lower Keltner Channel band |
| `bb_std` | float | Standard deviation for BB |
| `upper_bb_tight` | float | Upper BB (2.0 std dev) |
| `lower_bb_tight` | float | Lower BB (2.0 std dev) |
| `upper_bb_soft` | float | Upper BB (1.7 std dev) |
| `lower_bb_soft` | float | Lower BB (1.7 std dev) |
| `squeeze_tight_on` | boolean | Tight squeeze active |
| `squeeze_soft_on` | boolean | Soft squeeze active (not tight) |
| `squeeze_any_on` | boolean | Any squeeze active |
| `squeeze_release` | boolean | Squeeze just released |
| `momentum` | float | Momentum value |
| `momentum_sign` | int | Momentum direction (+1/0/-1) |
| `momentum_accel` | boolean | Momentum accelerating |

### State Definitions

| State | Condition | Interpretation |
|-------|-----------|----------------|
| `SQUEEZE_ON_TIGHT` | `squeeze_tight_on = true` | Maximum compression (BB 2.0 inside KC) |
| `SQUEEZE_ON_SOFT` | `squeeze_soft_on = true` | Moderate compression (BB 1.7 inside KC) |
| `SQUEEZE_RELEASED` | `squeeze_release = true` | First bar after squeeze ends |
| `NO_SQUEEZE` | All squeeze flags false | Normal volatility, no compression |

**Momentum Context:**
- `momentum > 0` and `momentum_accel = true` → Bullish expansion
- `momentum < 0` and `momentum_accel = false` → Bearish contraction
- Momentum sign gives directional bias during squeeze release

### Python Implementation
`shared/indicators/ttm_squeeze_adv.py`

Function: `compute_ttm_squeeze_adv(df, params=TTMSqueezeParams(), price_col='close')`

---

## Indicator Usage Rules

### Rule 1: No Modification During Execution
Indicators must not be modified, tuned, or reinterpreted during study execution.

If an indicator requires adjustment:
1. Update this specification first
2. Update the Python implementation in `shared/indicators/`
3. Re-run affected studies with version tracking

### Rule 2: Indicator Combination
Indicators may be combined only if explicitly stated in the study definition.

**Valid:** "Use Trend Strength where consensusClamped ≥ 70 AND is_nr7 = true"  
**Invalid:** Agent decides to "also check TTM Squeeze for confirmation" without study specification

### Rule 3: Signal vs Prediction
Indicator outputs are treated as **signals**, not predictions.

- A signal indicates a condition is met (e.g., "consensus ≥ 70")
- A signal does NOT predict future price movement
- Studies measure what historically happened after signals, not what "should" happen

### Rule 4: Parameter Defaults
Default parameters are canonical unless study definition specifies otherwise.

If a study requires non-default parameters:
- The study definition must explicitly state parameter values
- The rationale for non-default parameters must be documented
- Non-default parameters must be logged in study metadata

### Rule 5: Version Control
When indicator logic changes:
1. Update this specification with version number and date
2. Update Python implementation with matching version
3. Mark affected studies as requiring re-validation
4. Do not retroactively change past study results

---

**Document Status:** ✅ Active  
**Last Updated:** December 14, 2025  
**Related Files:**
- `shared/indicators/trend_strength_nr7.py` - Trend Strength implementation
- `shared/indicators/ttm_squeeze_adv.py` - TTM Squeeze implementation
- [docs/STUDY_PROMPT_LIBRARY.md](STUDY_PROMPT_LIBRARY.md) - Study definitions
- [docs/STUDY_EXECUTION_PROTOCOL.md](STUDY_EXECUTION_PROTOCOL.md) - Execution rules

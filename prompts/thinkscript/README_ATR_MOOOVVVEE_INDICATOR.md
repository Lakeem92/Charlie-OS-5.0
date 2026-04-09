# ATR Mooovvvee Indicator — Master Reference
### Trend Strength Line Indicator — GAP-AWARE v6.1
### ThinkOrSwim (TOS) Custom Lower Study
### Last Updated: March 9, 2026

---

## Table of Contents

1. [What This Indicator Does](#1-what-this-indicator-does)
2. [Architecture Overview](#2-architecture-overview)
3. [The Data Behind It — Study Sources](#3-the-data-behind-it--study-sources)
4. [Component 1: TrendScore Engine](#4-component-1-trendscore-engine)
5. [Component 2: Slope State + Divergence Detection](#5-component-2-slope-state--divergence-detection)
6. [Component 3: Gap Bias Module](#6-component-3-gap-bias-module)
7. [Component 4: Session ATR Tracker](#7-component-4-session-atr-tracker)
8. [Component 5: Follow-Through (FT) Engine](#8-component-5-follow-through-ft-engine)
9. [Component 6: Contrary Candle State Engine](#9-component-6-contrary-candle-state-engine)
10. [Component 7: Divergence Guard System](#10-component-7-divergence-guard-system)
11. [Label Reference — Every Label Explained](#11-label-reference--every-label-explained)
12. [How the Indicator Uses Data to Make Decisions](#12-how-the-indicator-uses-data-to-make-decisions)
13. [Input Parameters](#13-input-parameters)
14. [Visual Outputs](#14-visual-outputs)
15. [Limitations and Edge Cases](#15-limitations-and-edge-cases)

---

## 1. What This Indicator Does

This indicator is a **real-time gap day trade management system** built on top of a normalized trend strength engine. It answers one question during live trading:

> **"I'm on a gap day. What is the data telling me to do RIGHT NOW — enter, hold, tighten, or exit?"**

It is NOT a scanner. It is NOT a backtester. It is a **live decision support tool** that takes the statistical findings from three original research studies (totaling ~18,000+ gap events across 237 liquid US equities from Jan 2024–Mar 2026) and translates them into context-aware labels on a 5-minute intraday chart.

### What It Does in Practice

On any gap day ≥ 2%, the indicator:

1. **Classifies the gap** — direction, magnitude bucket, confidence tier
2. **Identifies the setup** — continuation (momentum with gap) or contrary candle (momentum against gap, i.e., fade/bounce)
3. **Tracks follow-through** — calculates the ATR-based FT level and tells you when it confirms
4. **Shows you your entry price** — latches and displays the FT bar's close as "ENTRY @ price"
5. **Tells you where you are in the trade** — time phases, HoD/LoD tracking, state engine messages with data-backed win rates
6. **Warns you about pullbacks and adverse moves** — with calibrated depth zones based on percentile distributions from the studies
7. **Catches divergences** — when the underlying trend slope contradicts the gap direction, it suppresses trade suggestions and warns "Divergence — Mean reversion possible"
8. **Monitors ATR exhaustion** — single-bar and session-level ATR consumption to flag overextension

All of this happens automatically. The trader loads the indicator on a 5-minute chart, and the labels update bar-by-bar with actionable, data-backed guidance.

---

## 2. Architecture Overview

The indicator has seven interlocking components, layered from foundation to surface:

```
┌─────────────────────────────────────────────────────┐
│  LAYER 7: DIVERGENCE GUARD SYSTEM                   │
│  Suppresses trade labels when slope contradicts gap  │
├─────────────────────────────────────────────────────┤
│  LAYER 6: CONTRARY CANDLE STATE ENGINE (v5.1)       │
│  HoD/LoD tracking → fadeState / bounceState          │
├─────────────────────────────────────────────────────┤
│  LAYER 5: FOLLOW-THROUGH (FT) ENGINE                │
│  FT latches, entry prices, E3 windows, time phases   │
├─────────────────────────────────────────────────────┤
│  LAYER 4: SESSION ATR TRACKER                        │
│  Daily ATR consumed %, single-bar ATR warnings       │
├─────────────────────────────────────────────────────┤
│  LAYER 3: GAP BIAS MODULE                            │
│  Gap classification, confidence tiers, bias labels    │
├─────────────────────────────────────────────────────┤
│  LAYER 2: SLOPE STATE + DIVERGENCE DETECTION         │
│  isRising / isDropping / neutral from smoothed slope │
├─────────────────────────────────────────────────────┤
│  LAYER 1: TRENDSCORE ENGINE                          │
│  Z-score normalized consensus of 3 methods → [-100,+100] │
└─────────────────────────────────────────────────────┘
```

Each layer feeds the one above it. The TrendScore produces the slope, the slope feeds the gap bias and divergence system, the gap bias triggers the FT engine, and the state engine sits on top of everything to produce the final labels.

---

## 3. The Data Behind It — Study Sources

This indicator is not opinion-based. Every label, threshold, win rate, and time phase is derived from three original quantitative studies run against real market data via Alpaca API:

### Study 1: Gap Execution Blueprint (Long Side)
- **Population:** 1,865 qualified events (gap-up ≥ 2%, non-bearish first candle, FT confirmed)
- **Universe:** 237 liquid US equities, Jan 2024–Mar 2026
- **Source data:** 5-minute bars from Alpaca (IEX feed)
- **Key findings used in indicator:**
  - 51% EOD win rate at E1 (breakout entry), but 69.2% at E3 (deepest pullback) with 6.47x R:R
  - 5-8% gaps are the sweet spot: 73.9% WR at E3, 8.36x R:R
  - Median HoD by gap bucket: 2-5%→170min, 5-8%→210min, 8-12%→145min, 12%+→85min
  - 77.9% of events pull back below entry; median pullback only -0.51%
  - 89.5% recover after pullback; 81.3% of worst pullbacks happen within 30 min
  - Only 9.9% make a second run at session high
  - Pullback depth zones: 25th=-0.00%, median=-0.51%, 75th=-1.18%, 90th=-2.83%

### Study 2: Gap-Down Execution Blueprint (Short Side)
- **Population:** 1,861 qualified events (gap-down ≥ 2%, non-bullish first candle, FT confirmed)
- **Key findings used in indicator:**
  - 45.4% all-event WR (shorts are harder), but continuation days = 2.37x R:R
  - LoD timing is the #1 differentiator: continuation days → median LoD at 315min (5h 15m)
  - HoD in first 5 min = 71.9% of continuation days (strongest confirmation)
  - 93.9% bounce above entry at some point — this is NORMAL, not failure
  - Bounce depth zones: median before LoD=+0.59%, 90th=+2.75%, median MAE=+2.15%
  - LoD > 4 hours = 75.8% short win rate
  - 8-12% gap-down = 56% WR (short sweet spot)

### Study 3: Gap Fade / Contrary Candle Study
- **Population:** 3,821 contrary candle events, 2,465 FT-confirmed (1,346 fades + 1,119 bounces)
- **Key findings used in indicator:**
  - Raw signal: gap-up + bearish bar-1 → 68.4% fade by EOD (no FT required)
  - Raw signal: gap-down + bullish bar-1 → 66.8% bounce by EOD
  - FT-confirmed fades: 51.3% WR, 1.22:1 R:R
  - FT-confirmed bounces: 51.4% WR, 1.17:1 R:R
  - **8-12% gap-down bounce = 62.3% WR, +1.10% avg, MFE > MAE** (the sweet spot)
  - HoD ≤ 5 min (topped at open) for fades = 66.6% WR → 71.2% with FT at open
  - LoD ≤ 5 min (bottomed at open) for bounces = 65.9% WR → 73.1% with FT at open
  - Continuation fade: LoD after 4hr = 82.7%, LoD in last hr = 91.3%, new highs last hr = 1%
  - Continuation bounce: HoD after 4hr = 76.1%, HoD in last hr = 85.2%, new lows last hr = 0%

### How Three Studies Become One Indicator

The indicator classifies every gap day into one of four paths:

| Path | Condition | Study Source | Direction |
|---|---|---|---|
| **Gap-Up Continuation** | Gap ≥ +2%, bar-1 NOT bearish | Study 1 | Long |
| **Gap-Down Continuation** | Gap ≤ -2%, bar-1 NOT bullish | Study 2 | Short |
| **Gap-Up Fade** | Gap ≥ +2%, bar-1 IS bearish | Study 3 (fade) | Short |
| **Gap-Down Bounce** | Gap ≤ -2%, bar-1 IS bullish | Study 3 (bounce) | Long |

Each path has its own FT logic, time phases, state engine, pullback zones, and label set — all driven by the data from the corresponding study.

---

## 4. Component 1: TrendScore Engine

### What It Is

The TrendScore is a multi-method consensus measurement of trend strength, normalized to a [-100, +100] scale. It is the foundational calculation that everything else builds on.

### Why Three Methods

No single trend measurement captures all market conditions well:
- **Price Change** catches sustained directional movement but is noisy on choppy days
- **EMA Slope** catches the smoothed direction of the moving average but lags during fast reversals
- **MA Distance** catches the spread between fast/slow averages but misses momentum changes within the spread

By averaging all three (after normalizing each to comparable scales), the consensus score is more robust than any single method.

### Calculation Pipeline

**Step 1: Raw signals (ATR-normalized)**

Each method produces a raw value normalized by ATR to make signals comparable across different-priced stocks:

```
Price Change:  rawPc = (close - close[20]) / ATR(14)
EMA Slope:     rawEmaSlope = (EMA(21) - EMA(21)[1]) / ATR(14)
               rawEmaSlopeSm = SMA(rawEmaSlope, 5)   ← smoothed
MA Distance:   rawMaDist = (EMA(20) - SMA(50)) / ATR(14)
```

**Step 2: Z-score normalization**

Each raw signal is converted to a z-score over a 100-bar lookback, then clamped to ±2.5 and scaled to [-1, +1]:

```
For each method:
  mean = Average(raw, 100)
  std  = StDev(raw, 100)
  z    = (raw - mean) / std
  z    = clamp(z, -2.5, +2.5)
  norm = clamp(z / 2.0, -1, +1)
```

This normalization is critical. It means a TrendScore of +70 on AAPL means the same thing as +70 on TSLA — it's "this stock is trending at its 70th percentile relative to its own recent history."

**Step 3: Consensus**

```
consensusRaw = (normPc + normEma + normMa) / 3
trendScore   = consensusRaw * 100     ← scale to [-100, +100]
```

### TrendScore Zones

| Range | Meaning |
|---|---|
| ≥ +70 | Overbought / Max bullish conviction |
| +40 to +69 | Strong bullish |
| +1 to +39 | Mild bullish |
| -39 to 0 | Mild bearish |
| -69 to -40 | Strong bearish |
| ≤ -70 | Oversold / Max bearish conviction |

### Visual Output

- **TrendLine plot:** Solid line colored green (≥70), dark green (40-69), light gray (0-39), orange (-40 to -1), red (≤-70)
- **Histogram:** Green bars above zero, red bars below zero
- **Signal Line:** 9-period EMA of TrendScore, shown as magenta dashed line
- **Overbought/Oversold clouds:** Red cloud above +70, cyan cloud below -70
- **Momentum acceleration shading:** Cyan strip at top when momentum accelerating up, orange strip when accelerating down

---

## 5. Component 2: Slope State + Divergence Detection

### What It Is

The slope measures how **fast** the TrendScore is changing — not where it is, but which direction it's moving and how quickly.

### Calculation

```
rawSlope = (trendScore - trendScore[5]) / 5     ← 5-bar rate of change
slope    = EMA(rawSlope, 3)                       ← smoothed

slopeState:
  slope > +0.25  → RISING  (1)
  slope < -0.25  → DROPPING (-1)
  otherwise      → NEUTRAL  (0)
```

The threshold of 0.25 defines the "neutral zone" — the slope must move decisively above or below this threshold to be classified as rising or dropping. This prevents noise from triggering false slope signals.

### The Slope Label

Always visible. Shows one of three states with context-aware coloring:

| State | Label Text | Color Logic |
|---|---|---|
| Rising | "TS SLOPE: RISING" | Green normally. CYAN if histogram is red (bearish TrendScore + rising slope = inflection) |
| Dropping | "TS SLOPE: DROPPING" | Red normally. YELLOW if histogram is green (bullish TrendScore + dropping slope = inflection) |
| Neutral | "TS SLOPE: NEUTRAL" | Light gray |

### Why Color Changes at Inflection Points

When the histogram is green (TrendScore > 0) but the slope is dropping, it means the trend is still positive but **losing momentum**. The yellow color warns that a crossover may be coming. Similarly, red histogram + rising slope (cyan) means bearish but recovering.

### How Slope Feeds Divergence

The slope state (`isRising`, `isDropping`) is the foundation of the divergence guard system (Component 7). When the slope contradicts the trade direction implied by the gap, the indicator suppresses trade suggestions entirely.

---

## 6. Component 3: Gap Bias Module

### What It Is

The gap bias module fires during the first 4 bars (20 minutes on 5-min chart) of regular trading hours. It classifies the gap and determines whether momentum aligns with or contradicts the gap direction.

### Gap Classification

```
gapPct = (dayOpen - prevDayClose) / prevDayClose × 100

Gap-Up:   gapPct ≥ +1.0%
Gap-Down: gapPct ≤ -1.0%
```

Note: The gap bias label uses a 1% minimum threshold (for general awareness), while the study system uses a 2% minimum (for the data-backed rules).

### Bias Determination

The module compares the gap direction against the **prior bar's slope state** (using `slope[1]` to avoid lookahead):

| Gap Direction | Prior Slope | Bias | Meaning |
|---|---|---|---|
| Gap-Up | Rising (+1) | **GO** | Momentum confirms gap direction — continuation likely |
| Gap-Up | Dropping (-1) | **FADE** | Momentum opposes gap — fade/reversal likely |
| Gap-Down | Dropping (-1) | **GO** | Momentum confirms gap direction — continuation likely |
| Gap-Down | Rising (+1) | **FADE** | Momentum opposes gap — bounce likely |
| Either | Neutral (0) | **MIXED** | No clear bias |

### Confidence Tiers

| Gap Size | Tier |
|---|---|
| ≥ 4.0% | HIGH |
| ≥ 2.0% | MED |
| < 2.0% | LOW |

### Prior-Bar TrendScore Zone

The label also shows the TrendScore's position (using `trendScore[1]`):

| TrendScore | Zone |
|---|---|
| ≥ 70 | OB (Overbought) |
| ≥ 30 | BULL |
| > -30 | NEUT |
| > -70 | BEAR |
| ≤ -70 | OS (Oversold) |

### The Gap Bias Label

Format: `{DIRECTION} | {TIER} | {gapPct}% | {ZONE}`

Examples:
- `GO UP | HIGH | +5.3% | BULL` — Large gap-up with momentum confirmation into bullish territory
- `FADE UP | MED | +2.8% | OB` — Gap-up but momentum is dropping while overbought
- `DN BOUNCE | HIGH | -6.1% | BEAR` — Large gap-down but momentum is rising (bounce expected)
- `DN CONT | LOW | -1.5% | NEUT` — Small gap-down with momentum confirmation

### Color Coding

| Bias | Gap Direction | Color |
|---|---|---|
| GO | Up | Green (intensity scales with tier: LongGoHigh/Med/Low) |
| GO | Down | Red (intensity scales with tier: ShortGoHigh/Med/Low) |
| FADE | Up | Orange/amber (FadeGapUp) |
| FADE | Down | Cyan (BounceGapDn) |
| MIXED | Either | Neutral gray |

### Volume Impulse Filter

The bias only fires if volume exceeds `1.5× the 50-bar average volume` (configurable). This filters out low-conviction gap opens. The volume filter can be disabled via the `requireVolumeImpulse` input.

---

## 7. Component 4: Session ATR Tracker

### What It Is

Tracks how much of the stock's typical daily range (ATR₁₄ on daily bars) has been consumed so far in the current session. Also monitors individual bar sizes for exhaustion warnings.

### Session ATR Consumed

```
sessionRange = dayHigh - dayLow (real-time)
sessionAtrPct = (sessionRange / priorDayATR) × 100
```

| ATR % | Label Color | Meaning |
|---|---|---|
| < 40% | Light gray | Range hasn't developed yet |
| 40-59% | Green | Normal development |
| 60-79% | Yellow | Above average range — be aware |
| 80-99% | Orange | Full ATR consumed — extension territory |
| ≥ 100% | Red | Beyond normal range — exhaustion likely |

### Single-Bar ATR Warnings

Monitors each 5-minute candle's range against the prior day's ATR:

```
barAtrPct = (barHigh - barLow) / priorDayATR × 100
```

| Threshold | Label | Color | Meaning |
|---|---|---|---|
| ≥ 180% | "1-BAR X% ATR — NO NEW ENTRIES" | Red | One candle consumed nearly 2 full days of range. Extreme. No new positions. |
| ≥ 80% | "1-BAR X% ATR EXHAUSTION" | Orange | One candle consumed most of a day's range. Move likely exhausted. |
| ≥ 70% | "1-BAR X% ATR WARNING" | Yellow | Large single-bar move. Caution. |

---

## 8. Component 5: Follow-Through (FT) Engine

### The Core Concept

Follow-Through is the moment when the opening gap direction is **confirmed by price action** — the stock doesn't just gap, it continues moving in the gap direction beyond a data-calibrated threshold.

### FT Level Calculation

```
priorDayATR = 14-period Wilder's ATR on daily bars (using prior day's value)

Long FT Level:  dayOpen + (priorDayATR × 0.40)
Short FT Level: dayOpen - (priorDayATR × 0.40)
```

The 0.40 multiplier (40% of ATR) was chosen because it represents a meaningful intraday move relative to the stock's typical daily range — enough to filter noise but not so much that it misses the early move.

### FT Logic by Path

| Path | FT Condition | Entry Direction |
|---|---|---|
| Gap-Up Continuation | Close ≥ Long FT Level AND bar-1 not bearish | Long |
| Gap-Down Continuation | Close ≤ Short FT Level AND bar-1 not bullish | Short |
| Gap-Up Fade (contrary) | Close ≤ Short FT Level AND bar-1 IS bearish | Short |
| Gap-Down Bounce (contrary) | Close ≥ Long FT Level AND bar-1 IS bullish | Long |

Note that contrary candles use the **opposite** FT level — a gap-up fade needs downside FT (price falling to the short FT level), because the trade is a short.

### FT Latch

Once FT fires, it **latches for the rest of the session**. It cannot un-fire. This is implemented via `CompoundValue` that sets to 1 on the FT bar and stays 1 until the next session start.

### Entry Price

The **close of the FT bar** is latched as the entry price and displayed for the rest of the day. This is the reference point for all pullback/adverse move calculations.

### E3 Window

The E3 window is the 6-bar (~30 minute) period immediately after FT fires. During this window, the indicator shows "E3 ZONE — HOLD PB" because the data shows:

- **E3 entry (deepest pullback in this window): 69.2% WR, 6.47x R:R** (vs 51% / 0.82x for breakout entry)
- In 5-8% gaps: **73.9% WR, 8.36x R:R**
- This is the single best trade in the entire dataset

The E3 label tells the trader: "A pullback right now is the ENTRY, not the failure."

### Time Phases (Long Continuation)

After the E3 window, the indicator transitions through time-based phases calibrated to the gap bucket's median HoD timing:

| Phase | Condition | Label | Meaning |
|---|---|---|---|
| 1 — Early | barsSinceOpen < 12 (< 1hr) | "HOLD — TOO EARLY TO CUT" | 81.3% of worst pullbacks happen within 30 min. Don't panic. |
| 2 — Building | 1hr to median HoD window | "PROFIT BUILDING" | The move is developing. Exiting before noon leaves 73-93% of returns on the table. |
| 3 — HoD Window | ±4 bars around median HoD bar | "PROFIT ZONE CLOSING" | Approaching the median time when the session high is typically set. Consider tightening. |
| 4 — Trail | Past HoD window | "TRAIL ZONE — 90% DONE AT HOD" | Only 9.9% of events make a second run at HoD. Trail the stop. |

The median HoD bar varies by gap bucket:
- 2-5%: bar 34 (~170 min, 11:20 CT)
- 5-8%: bar 42 (~210 min, 12:00 CT)
- 8-12%: bar 29 (~145 min, 10:55 CT)
- 12%+: bar 17 (~85 min, 9:55 CT)

### Time Phases (Short Continuation)

Short phases are different because gap-down behavior is asymmetric. As of v6.1, the short phases use **per-bucket median LoD timing** (mirroring the long side's per-bucket HoD), not flat time thresholds:

**Median LoD bar by gap bucket:**
- 2-5%: bar 64 (~320 min, ~2:10 CT)
- 5-8%: bar 65 (~325 min, ~2:15 CT)
- 8-12%: bar 59 (~295 min, ~1:45 CT)
- 12%+: bar 54 (~270 min, ~1:20 CT)

| Phase | Condition | Label | Meaning |
|---|---|---|---|
| 1 — Early | barsSinceOpen < 12 (< 1hr) | "HOLD — TOO EARLY TO COVER" | Bounces are normal. 93.9% bounce above entry. Don't cover. |
| 2 — Working | 1hr to shortLoDBar − 4 | "SHORT WORKING \| LOD AVG ~Xm" | Shows per-bucket median LoD time. Don't cut before LoD zone. |
| 3 — LoD Zone | shortLoDBar ± 4 bars | "LOD ZONE 76% \| MAKING NEW LOWS — TRAIL" or "LOD ZONE \| HOLD FOR LOD" | If LoD refreshed in this window, 76% WR → trail. If not, hold for it. |
| 4 — Past LoD Avg | Past shortLoDBar + 4 | "PAST LOD AVG \| 46% LOD IN LAST HR" | 46.3% of continuation days make their LoD in the final hour. |

### Pullback / Adverse Move Zones

After FT fires, the indicator continuously calculates how far price has moved against the entry:

**Long Pullback Zones (from entry):**

| Depth | Label | Color | Data Source |
|---|---|---|---|
| 0.51-1.18% | "PB X% — NORMAL" | Green | Median to 75th percentile of pullback distribution |
| 1.18-2.83% | "PB X% — DEEP BUT 90% RECOVER" | Orange | 75th to 90th percentile |
| ≥ 2.83% | "PB X% — EVALUATE EXIT" | Red | Past 90th percentile — only 9% of events get here |

**Short Bounce Zones (from entry) — v6.1: Per-Bucket MAE:**

As of v6.1, short continuation bounce thresholds scale by gap bucket instead of using flat values. Source: GAP_STUDIES_MASTER_REFERENCE Section 3.

| Bucket | Median MAE | Cover Stop |
|---|---|---|
| 2-5% | 1.90% | 4.25% |
| 5-8% | 2.76% | 5.50% |
| 8-12% | 3.44% | 7.00% |
| 12%+ | 5.35% | 7.50% |

| Depth | Label | Color | Data Source |
|---|---|---|---|
| 0.30% to shortMAE | "BOUNCE X% — NORMAL" | Green | Below median MAE for this bucket |
| shortMAE to shortCoverStop | "BOUNCE X% — AT MEDIAN MAE" | Orange | At/past median, within cover stop |
| ≥ shortCoverStop | "BOUNCE X% — PAST COVER STOP — TIGHTEN" | Red | Past cover stop for this bucket |

---

## 9. Component 6: Contrary Candle State Engine (v5.1)

### What It Is

The state engine is the most sophisticated component of the indicator. It tracks **when** the session high and low were set (not just where they are) and uses this timing data to produce real-time probability estimates of trade continuation vs failure.

### Why HoD/LoD Timing Matters

The breakthrough finding from the Continuation Day Deep Dive was that the TIMING of when the session high/low was last refreshed is the single strongest predictor of whether a trade will work:

**For fades (short on gap-up):**
- HoD in first 5 min (topped at open): **66.6% WR** → **71.2% with FT at open**
- HoD after 30 min (still making highs): **only 17% continuation**
- LoD after 4 hours (still grinding down): **82.7% WR**
- LoD in last hour: **91.3% WR**
- HoD in last hour: **1% WR** (trade is dead)

**For bounces (long on gap-down):**
- LoD in first 5 min (bottomed at open): **65.9% WR** → **73.1% with FT at open**
- LoD after 30 min (still making lows): **only 17.9% continuation**
- HoD after 4 hours (still grinding up): **76.1% WR**
- HoD in last hour: **85.2% WR**
- LoD in last hour: **0% WR** (trade is dead)

### How It Tracks

```
iHi = running session high (Max of all highs since open)
iLo = running session low (Min of all lows since open)

hodBar = bar number when session high was LAST refreshed
         (resets when a new bar's high exceeds the running high)
lodBar = bar number when session low was LAST refreshed
         (resets when a new bar's low undercuts the running low)
```

### Fade State Engine (gap-up + bearish bar-1 = short)

The `fadeState` variable evaluates conditions in priority order and produces exactly one label at all times:

| State | Value | Condition | WR | Label | Color |
|---|---|---|---|---|---|
| REVERSED | 11 | Price hit bullish FT — fade dead | 16% | "FADE REVERSED 16% \| EXIT NOW \| RALLY TO FT" | Red |
| DEAD | 10 | Last hour + new session highs | 1% | "FADE DEAD 1% \| EXIT NOW" | Red |
| LOD_LAST_HR | 9 | Last hour + LoD refreshed in last hour | 91% | "FADE 91% \| LOD LAST HR -- TRAIL" | Magenta |
| GRINDING | 8 | Past 4hr + LoD refreshed past 4hr | 83% | "FADE 83% \| MAKING LOWS -- HOLD" | Magenta |
| WEAK | 7 | Past 30min + HoD refreshed past 30min | 17% | "FADE WEAK 17% \| NEW HIGHS PAST 30M" | Red |
| BEST | 6 | HoD at open + FT at open | 71% | "FADE 71% \| TOPPED+FT AT OPEN" | Pink |
| TOPPED | 5 | HoD at open (any FT time) | 67% | "FADE 67% \| TOPPED AT OPEN -- HOLD" | Pink |
| CAUTION | -1 | New highs before 30min, HoD not at open | 29% | "FADE 29% \| NEW HIGHS -- TIGHTEN" | Yellow |
| E3 | 2 | Within E3 window | — | "FADE HOLD — BOUNCE NORMAL TO +X%" (per-bucket MAE) | Orange |
| EARLY | 3 | First hour | — | "FADE WORKING" | Orange |
| BUILDING | 4 | Mid-session default | — | "FADE BUILDING" | Orange |

### Bounce State Engine (gap-down + bullish bar-1 = long)

Mirror of the fade engine with symmetric conditions:

| State | Value | Condition | WR | Label | Color |
|---|---|---|---|---|---|
| REVERSED | 11 | Price hit bearish FT — bounce dead | 11% | "BOUNCE REVERSED 11% \| EXIT NOW \| DROP TO FT" | Red |
| DEAD | 10 | Last hour + new session lows | 0% | "BOUNCE DEAD 0% \| EXIT NOW" | Red |
| HOD_LAST_HR | 9 | Last hour + HoD refreshed in last hour | 85% | "BOUNCE 85% \| HOD LAST HR -- TRAIL" | Magenta |
| GRINDING | 8 | Past 4hr + HoD refreshed past 4hr | 76% | "BOUNCE 76% \| MAKING HIGHS -- HOLD" | Magenta |
| WEAK | 7 | Past 30min + LoD refreshed past 30min | 18% | "BOUNCE WEAK 18% \| NEW LOWS PAST 30M" | Red |
| BEST | 6 | LoD at open + FT at open | 73% | "BOUNCE 73% \| BOTTOMED+FT AT OPEN" | Cyan |
| BOTTOMED | 5 | LoD at open (any FT time) | 66% | "BOUNCE 66% \| BOTTOMED AT OPEN -- HOLD" | Cyan |
| CAUTION | -1 | New lows before 30min, LoD not at open | 25% | "BOUNCE 25% \| NEW LOWS -- TIGHTEN" | Yellow |
| E3 | 2 | Within E3 window | — | "BOUNCE HOLD — PB NORMAL TO -X%" (per-bucket MAE) | BounceGapDn |
| EARLY | 3 | First hour | — | "BOUNCE WORKING" | BounceGapDn |
| BUILDING | 4 | Mid-session default | — | "BOUNCE BUILDING" | BounceGapDn |

### 8-12% Gap Sweet Spot

The labels include the gap bucket on every message. The data shows:
- **8-12% gap-down bounces: 62.3% WR** (vs 50.1% for 2-5%)
- With bottomed-at-open filter: **76.0% WR**
- Continuation days: +4.42% avg return, 6.59% MFE, 2.72x MFE/MAE

This is why 8-12% bounces show "8-12% SWEET" in cyan, while 8-12% fades show "8-12% AVOID" because that bucket has only 45.7% WR for fades.

### Adverse Move Zones (Contrary Candle Paths)

**Fade adverse (bounce against short) — v6.1: Per-Bucket MAE:**

Source: GAP_STUDIES_MASTER_REFERENCE Section 4.

| Bucket | Median MAE (fadeMAE) | 75th Pctl (fadeMAE75) |
|---|---|---|
| 2-5% | 1.98% | 3.58% |
| 5-8% | 2.98% | 5.39% |
| 8-12% | 4.13% | 7.48% |
| 12%+ | 6.67% | 12.07% |

| Depth | Label | Source |
|---|---|---|
| 0.30% to fadeMAE | "BOUNCE X% -- NORMAL" | Below median MAE for this bucket |
| fadeMAE to fadeMAE75 | "BOUNCE X% -- DEEP" | Median to 75th percentile |
| ≥ fadeMAE75 | "BOUNCE X% -- EVALUATE" | Past 75th percentile |

**Bounce adverse (pullback against long) — v6.1: Per-Bucket MAE:**

Source: GAP_STUDIES_MASTER_REFERENCE Section 5.

| Bucket | Median MAE (bounceMAE) | 75th Pctl (bounceMAE75) |
|---|---|---|
| 2-5% | 1.72% | 3.30% |
| 5-8% | 2.69% | 5.16% |
| 8-12% | 3.27% | 6.28% |
| 12%+ | 4.54% | 8.72% |

| Depth | Label | Source |
|---|---|---|
| 0.30% to bounceMAE | "PB X% -- NORMAL" | Below median MAE for this bucket |
| bounceMAE to bounceMAE75 | "PB X% -- DEEP" | Median to 75th percentile |
| ≥ bounceMAE75 | "PB X% -- EVALUATE" | Past 75th percentile |

---

## 10. Component 7: Divergence Guard System

### The Problem It Solves

A gap-up with a bearish first candle is a "fade" setup (short). But what if the underlying trend is aggressively bullish (slope rising)? The gap-up is in the direction of the trend, and the bearish candle is just noise — going short here means fighting the prevailing momentum.

Similarly, a gap-down continuation (short) shouldn't be recommended when the trend slope is rising, because the momentum is against the short.

### The Logic

The divergence guard checks whether the TS slope state contradicts the trade direction:

| Trade Direction | Contradicting Slope | Result |
|---|---|---|
| Long (gap-up continuation) | isDropping = true | **Suppressed** — divergence |
| Long (gap-down bounce) | isDropping = true | **Suppressed** — divergence |
| Short (gap-down continuation) | isRising = true | **Suppressed** — divergence |
| Short (gap-up fade) | isRising = true | **Suppressed** — divergence |

### What Happens on Divergence

When a divergence is detected:

1. **A pink label appears:** `"Divergence — Mean reversion possible"` (color: FadePink = hot pink, RGB 255/105/180)
2. **All trade suggestion labels for that path are suppressed** — no "AWAIT FT", no state engine labels, no entry price, no time phase labels
3. **Position management labels (pullback/adverse zones) are NOT suppressed** — if you're already in a trade, you still need to see how deep the adverse move is

### Why "Mean Reversion Possible" (Not "Stand Down")

The label text is deliberately nuanced. It doesn't say "don't trade" — it says the gap is diverging from the underlying momentum, which means instead of continuation, mean reversion back toward the trend is more likely. This is information, not a command.

### When Divergence Labels Show

The divergence label fires when ALL of these are true:
1. There is a qualifying gap (≥ 2%)
2. The gap path is identified (continuation or contrary)
3. The slope state contradicts the trade direction

The label will NOT show if there's no qualifying gap, or if the slope is neutral (only rising/dropping trigger it).

---

## 11. Label Reference — Every Label Explained

### Always-On Labels

| Label | Condition | Color | Purpose |
|---|---|---|---|
| TS SLOPE: RISING/DROPPING/NEUTRAL | Always | Green/Red/Yellow/Cyan/Gray | Current slope state of TrendScore |
| GAP: -- | Outside open window | Gray | No gap bias data outside first 20 min |
| NO GAP | In window, gap < 1% | Gray | No qualifying gap today |
| GO UP / DN CONT / FADE UP / DN BOUNCE | In open window + qualifying gap | Varies | Gap bias classification |
| ATR: X% | Always | Gray→Green→Yellow→Orange→Red | How much of daily range consumed |
| NO GAP STUDY | No gap ≥ 2% | Light gray | Study rules don't apply today |

### Single-Bar ATR Warnings (conditional)

| Label | Condition | Color |
|---|---|---|
| 1-BAR X% ATR — NO NEW ENTRIES | barRange ≥ 180% of ATR | Red |
| 1-BAR X% ATR EXHAUSTION | barRange ≥ 80% of ATR | Orange |
| 1-BAR X% ATR WARNING | barRange ≥ 70% of ATR | Yellow |

### Divergence Labels (all four paths)

| Label | Condition | Color |
|---|---|---|
| Divergence — Mean reversion possible | Long path + slope dropping, OR short path + slope rising | Pink (FadePink) |

### Gap-Up Continuation (Long) Labels

| Label | Condition | Color |
|---|---|---|
| AWAIT FT {level} \| {bucket} | Pre-FT, slope not dropping | Yellow |
| E3 ZONE — HOLD PB \| {bucket} | FT confirmed, within 6-bar E3 window | Cyan |
| HOLD — TOO EARLY TO CUT \| {bucket} | FT confirmed, first hour, past E3 | Green |
| PROFIT BUILDING \| {bucket} | Past 1hr, before median HoD window | Green |
| PROFIT ZONE CLOSING \| {bucket} | ±4 bars around median HoD | Yellow |
| TRAIL ZONE — 90% DONE AT HOD \| {bucket} | Past median HoD window | Orange |
| ENTRY @ {price} (FT bar close) | FT confirmed, entry latched | Green |
| PB X% — NORMAL | FT confirmed, pullback 0.51-1.18% | Green |
| PB X% — DEEP BUT 90% RECOVER | Pullback 1.18-2.83% | Orange |
| PB X% — EVALUATE EXIT | Pullback ≥ 2.83% | Red |

### Gap-Down Continuation (Short) Labels

| Label | Condition | Color |
|---|---|---|
| AWAIT FT {level} \| {bucket} | Pre-FT, slope not rising | Yellow |
| E3 ZONE — 85% BOUNCE ABOVE ENTRY \| HOLD \| {bucket} | FT confirmed, within E3 window | Cyan |
| HOLD — TOO EARLY TO COVER \| {bucket} | First hour, past E3 | Red |
| SHORT WORKING \| LOD AVG ~Xm \| {bucket} | 1hr to LoD zone (per-bucket) | Red |
| LOD ZONE 76% \| MAKING NEW LOWS — TRAIL \| {bucket} | LoD zone ± 4 bars, LoD refreshed | Magenta |
| LOD ZONE \| HOLD FOR LOD \| {bucket} | LoD zone ± 4 bars, LoD not yet refreshed | Red |
| PAST LOD AVG \| 46% LOD IN LAST HR \| {bucket} | Past LoD zone | Orange |
| LOD AVG ~Xm \| ~X:XX CT | Pre-LoD, informational | Light gray |
| LOD <30M — 87% V-BOTTOM — EVALUATE | LoD bar ≤ 5, past bar 6, before bar 24 | Red |
| PRICE ABOVE OPEN — V-BOTTOM LIKELY | Close > dayOpen, past bar 6, before bar 24 | Red |
| ENTRY @ {price} (FT bar close) | FT confirmed, entry latched | Red |
| BOUNCE X% — NORMAL | Bounce 0.30% to shortMAE (per-bucket) | Green |
| BOUNCE X% — AT MEDIAN MAE | Bounce shortMAE to shortCoverStop | Orange |
| BOUNCE X% — PAST COVER STOP — TIGHTEN | Bounce ≥ shortCoverStop (per-bucket) | Red |

### Gap-Up Fade (Contrary Short) Labels

| Label | Condition | Color |
|---|---|---|
| FADE ALERT 68% \| AWAIT FT {level} \| {bucket} | Pre-FT, slope not rising | Orange (Yellow for 8-12%) |
| FADE 71% \| TOPPED+FT AT OPEN \| {bucket} | State 6: HoD at open + FT at open | Pink |
| FADE 67% \| TOPPED AT OPEN -- HOLD \| {bucket} | State 5: HoD at open | Pink |
| FADE 29% \| NEW HIGHS -- TIGHTEN \| {bucket} | State -1: New highs before 30m | Yellow |
| FADE WEAK 17% \| NEW HIGHS PAST 30M \| {bucket} | State 7: HoD refreshed past 30m | Red |
| FADE 83% \| MAKING LOWS -- HOLD \| {bucket} | State 8: LoD refreshed past 4hr | Magenta |
| FADE 91% \| LOD LAST HR -- TRAIL \| {bucket} | State 9: LoD in last hour | Magenta |
| FADE DEAD 1% \| EXIT NOW | State 10: HoD in last hour | Red |
| FADE REVERSED 16% \| EXIT NOW \| RALLY TO FT | State 11: Price hit bullish FT — fade dead | Red |
| FADE HOLD — BOUNCE NORMAL TO +X% \| {bucket} | State 2: In E3 window (per-bucket MAE) | Orange |
| FADE WORKING \| {bucket} | State 3: Early session | Orange |
| FADE BUILDING \| {bucket} | State 4: Mid-session | Orange |
| FADE LOD AVG ~290m (CONT) | Pre-bar 58, informational | Orange |
| ENTRY @ {price} (FT bar close) | FT confirmed, entry latched | Orange |
| BOUNCE X% -- NORMAL | Adverse 0.30% to fadeMAE (per-bucket) | Pink |
| BOUNCE X% -- DEEP | Adverse fadeMAE to fadeMAE75 | Orange |
| BOUNCE X% -- EVALUATE | Adverse ≥ fadeMAE75 (per-bucket) | Red |

### Gap-Down Bounce (Contrary Long) Labels

| Label | Condition | Color |
|---|---|---|
| BOUNCE ALERT 67% \| AWAIT FT {level} \| {bucket} | Pre-FT, slope not dropping | Cyan (for 8%+) or BounceGapDn |
| BOUNCE 73% \| BOTTOMED+FT AT OPEN \| {bucket} | State 6: LoD at open + FT at open | Cyan |
| BOUNCE 66% \| BOTTOMED AT OPEN -- HOLD \| {bucket} | State 5: LoD at open | Cyan |
| BOUNCE 25% \| NEW LOWS -- TIGHTEN \| {bucket} | State -1: New lows before 30m | Yellow |
| BOUNCE WEAK 18% \| NEW LOWS PAST 30M \| {bucket} | State 7: LoD refreshed past 30m | Red |
| BOUNCE 76% \| MAKING HIGHS -- HOLD \| {bucket} | State 8: HoD refreshed past 4hr | Magenta |
| BOUNCE 85% \| HOD LAST HR -- TRAIL \| {bucket} | State 9: HoD in last hour | Magenta |
| BOUNCE DEAD 0% \| EXIT NOW | State 10: LoD in last hour | Red |
| BOUNCE REVERSED 11% \| EXIT NOW \| DROP TO FT | State 11: Price hit bearish FT — bounce dead | Red |
| BOUNCE HOLD — PB NORMAL TO -X% \| {bucket} | State 2: In E3 window (per-bucket MAE) | BounceGapDn |
| BOUNCE WORKING \| {bucket} | State 3: Early session | BounceGapDn |
| BOUNCE BUILDING \| {bucket} | State 4: Mid-session | BounceGapDn |
| BOUNCE HOD AVG ~245m (CONT) | Pre-bar 49, informational | BounceGapDn |
| ENTRY @ {price} (FT bar close) | FT confirmed, entry latched | BounceGapDn |
| PB X% -- NORMAL | Adverse 0.30% to bounceMAE (per-bucket) | Cyan |
| PB X% -- DEEP | Adverse bounceMAE to bounceMAE75 | Orange |
| PB X% -- EVALUATE | Adverse ≥ bounceMAE75 (per-bucket) | Red |

---

## 12. How the Indicator Uses Data to Make Decisions

### Decision Tree (What Fires When)

```
Is there a qualifying gap ≥ 2%?
├── NO → "NO GAP STUDY" (gray) → STOP
└── YES
    ├── Is first candle contrary (bearish on gap-up / bullish on gap-down)?
    │   ├── YES → CONTRARY CANDLE PATH
    │   │   ├── Gap-up + bearish bar-1 → FADE (short side)
    │   │   │   ├── Is slope RISING? → "Divergence — Mean reversion possible" (pink)
    │   │   │   └── Slope not rising → FT engine + fade state engine
    │   │   └── Gap-down + bullish bar-1 → BOUNCE (long side)
    │   │       ├── Is slope DROPPING? → "Divergence — Mean reversion possible" (pink)
    │   │       └── Slope not dropping → FT engine + bounce state engine
    │   └── NO → CONTINUATION PATH
    │       ├── Gap-up → LONG CONTINUATION
    │       │   ├── Is slope DROPPING? → "Divergence — Mean reversion possible" (pink)
    │       │   └── Slope not dropping → FT engine + long time phases
    │       └── Gap-down → SHORT CONTINUATION
    │           ├── Is slope RISING? → "Divergence — Mean reversion possible" (pink)
    │           └── Slope not rising → FT engine + short time phases
```

### The Data Chain (How a Number Becomes a Label)

Here is the full chain for a single example: TSLA gaps down -6.2% with a bullish first candle (gap-down bounce path):

1. **TrendScore** computes to -45 (bearish but not extreme)
2. **Slope** = -0.8 (below -0.25 threshold → `isDropping = true`)
3. **Gap module** classifies as gap-down, slope dropping → **divergence detected for long path**
4. **Divergence guard** fires: slope is dropping, bounce is a long trade → **"Divergence — Mean reversion possible"** (pink)
5. All bounce suggestion labels suppressed (no AWAIT FT, no state engine, no entry price)
6. If trader already has a bounce position, adverse move labels still show

Now change the slope to +0.4 (rising):

1. **TrendScore** computes to -20 (mild bearish, but slope is rising)
2. **Slope** = +0.4 (above +0.25 → `isRising = true`)
3. **Gap module** classifies as gap-down, slope rising → **FADE bias** (DN BOUNCE label)
4. **No divergence** (isDropping is false, so bounce path is clear)
5. **FT level** = $90 open + ($5 ATR × 0.40) = $92.00
6. Bar-2 closes at $92.15 → **FT fires**, ftBounceEntry = $92.15
7. **LoD check**: LoD bar = 0 (the open), barsSinceOpen = 1 → **bounceState = 6 (BEST)**
8. **Label**: `"BOUNCE 73% | BOTTOMED+FT AT OPEN | 5-8%"` (cyan)
9. **Entry label**: `"ENTRY @ 92.15 (FT bar close)"` (BounceGapDn color)

### Why Each Threshold Exists

| Threshold | Value | Origin |
|---|---|---|
| FT at 40% ATR | 0.40 × ATR₁₄ | Calibrated to capture meaningful intraday moves without over-filtering |
| Slope neutral threshold | ±0.25 | Prevents noise from triggering slope state changes |
| Min gap for study | 2.0% | Studies only have data for gaps ≥ 2%; below this, the rules don't apply |
| Min gap for bias label | 1.0% | General awareness — smaller gaps noted but don't trigger study logic |
| E3 window | 6 bars (30 min) | 81.3% of deepest pullbacks happen within 30 min of FT |
| Contrary candle body threshold | 40% of range | Standard candle classification — body > 40% = decisive, ≤ 40% = indecisive |
| Long pullback zones | 25th/median/75th/90th percentiles | Directly from study distributions |
| Short/Fade/Bounce MAE zones | Per-bucket median + 75th pctl (v6.1) | GAP_STUDIES_MASTER_REFERENCE Sections 3/4/5 |
| Long HoD bar | Per-bucket (17/29/34/42) | Median HoD timing from gap_execution_blueprint |
| Short LoD bar | Per-bucket (54/59/64/65) | Median LoD timing from gap_down_execution_blueprint |
| HoD/LoD time thresholds | 6/48 (30m/4hr) | Mapped from study time windows to 5-min bar counts |
| V-bottom threshold | LoD bar ≤ 5 | 87% V-bottom rate when LoD set within first 30 min (n=366) |

---

## 13. Input Parameters

### Core TrendScore

| Input | Default | Description |
|---|---|---|
| showConsensus | yes | Show consensus mode |
| method | "Consensus" | Which method to display (Consensus, Price Change, EMA Slope, MA Distance) |
| pcLookback | 20 | Price change lookback bars |
| emaLen | 21 | EMA length for slope method |
| emaSlopeSmooth | 5 | Smoothing for EMA slope |
| ma1Type / ma1Len | EMA / 20 | Fast MA for distance method |
| ma2Type / ma2Len | SMA / 50 | Slow MA for distance method |
| atrLen | 14 | ATR period for normalization |
| normLen | 100 | Z-score lookback |
| zClamp | 2.5 | Max z-score before clamping |
| zToUnitRange | 2.0 | Divisor to convert z-score to ±1 range |

### Visuals

| Input | Default | Description |
|---|---|---|
| showHistogram | yes | Show TrendScore histogram bars |
| showMomentum | yes | Show momentum acceleration shading |
| showSignalLine | yes | Show 9-period EMA signal line |
| signalLength | 9 | Signal line EMA period |
| useColorGradient | yes | Color TrendLine by value zones |

### Slope

| Input | Default | Description |
|---|---|---|
| showSlopeLabel | yes | Show TS SLOPE label |
| slopeLen | 5 | Rate of change lookback |
| slopeSmoothLen | 3 | EMA smoothing for slope |
| slopeNeutralThreshold | 0.25 | ±threshold for rising/dropping classification |

### Gap Bias

| Input | Default | Description |
|---|---|---|
| showGapBiasLabel | yes | Show gap bias label |
| rthStartTime | 0930 | Regular trading hours start (ET) |
| openWindowBars | 4 | How many bars the bias label stays active |
| minAbsGapPct | 1.0 | Minimum gap size for bias label |
| requireVolumeImpulse | yes | Require volume confirmation |
| volLookback / volMult | 50 / 1.5 | Volume average period and spike multiplier |
| usePriorBarForBias | yes | Use slope[1] instead of current slope for bias |
| gapTierMed / gapTierHigh | 2.0 / 4.0 | Gap size thresholds for confidence tiers |

### ATR Warnings

| Input | Default | Description |
|---|---|---|
| showATRWarning | yes | Show session ATR and single-bar warnings |
| atrWarnPct | 70 | Single-bar warning threshold (% of daily ATR) |
| atrExhaustPct | 80 | Single-bar exhaustion threshold |
| atrExtremePct | 180 | Single-bar extreme threshold (no new entries) |

### Gap Study / FT

| Input | Default | Description |
|---|---|---|
| showFTLabel | yes | Show all FT/study labels |
| ftAtrPct | 0.40 | FT level = Open ± (ATR × this value) |
| minGapForStudy | 2.0 | Minimum gap % for study rules to apply |
| e3WindowBars | 6 | E3 window duration (bars after FT) |

---

## 14. Visual Outputs

### Plots

| Plot | Description | Style |
|---|---|---|
| TrendLine | TrendScore value [-100, +100] | Solid line, weight 3, color-graded |
| SignalLinePlot | 9-period EMA of TrendScore | Magenta dashed, weight 2 |
| Histogram | TrendScore as histogram bars | Green (≥0) / Red (<0), weight 3 |
| ZeroLine | Zero reference | Light gray dashed |
| OverboughtLine | +70 level | Red dashed |
| OversoldLine | -70 level | Cyan dashed |

### Clouds

| Cloud | Description |
|---|---|
| Red cloud above +70 | Overbought zone shading |
| Cyan cloud below -70 | Oversold zone shading |
| Cyan strip at 95-100 | Momentum accelerating upward |
| Orange strip at 95-100 | Momentum accelerating downward |

### Color Definitions

| Name | RGB | Usage |
|---|---|---|
| LongGoHigh | (0, 255, 140) | Strong long continuation bias |
| LongGoMed | (0, 220, 120) | Medium long continuation bias |
| LongGoLow | (100, 255, 170) | Low long continuation bias |
| ShortGoHigh | (255, 70, 70) | Strong short continuation bias |
| ShortGoMed | (235, 95, 95) | Medium short continuation bias |
| ShortGoLow | (255, 145, 145) | Low short continuation bias |
| FadeGapUp | (255, 190, 0) | Gap-up fade labels (amber) |
| FadePink | (255, 105, 180) | High-probability fade states + divergence labels |
| BounceGapDn | (0, 210, 255) | Gap-down bounce labels (light blue) |
| Watch | (195, 205, 220) | Inactive/no-data states |
| Neutral | (235, 235, 235) | Mixed/no-bias states |
| E3Zone | (0, 230, 255) | E3 pullback window labels |

---

## 15. Limitations and Edge Cases

### Data Boundaries
- All study data is from **Jan 2024 – Mar 2026** on **237 liquid US equities**. The rules may not generalize to illiquid stocks, non-US markets, or fundamentally different market regimes.
- Gap-down continuation has a **45.4% all-event WR** — the short side is inherently harder. The indicator's value is in identifying the subset of continuation days (2.37x R:R) vs V-bottoms.

### Timeframe Dependency
- Designed for **5-minute intraday charts**. All bar counts (E3 window = 6 bars, HoD bar = 34, etc.) assume 5-minute aggregation.
- HoD/LoD tracking uses strict `high > iHi[1]` comparisons — equal highs/lows do NOT count as a refresh.

### First Candle Classification
- The contrary candle check uses the **first 5-minute bar** only. If the first bar is a doji (body ≤ 40% of range), it's classified as "not contrary" and routes to the continuation path — even if the second bar is strongly contrary.

### Slope Lag
- The slope uses a 5-bar lookback smoothed with a 3-bar EMA. This means the slope state lags a few bars behind actual momentum changes. A fast reversal may not immediately flip the divergence guard.
- The gap bias module uses `slope[1]` (prior bar's slope) to avoid the current bar's price affecting the classification.

### Session Boundaries
- Uses `SecondsFromTime(0930)` for session detection. Extended hours / pre-market data before 9:30 ET is ignored.
- All latches (FT, entry price, state engine) reset at the session start bar.

### Overlapping Labels
- In rare cases, multiple label conditions can be true simultaneously (e.g., adverse move zone + state engine label). TOS displays all true labels left-to-right. This is intentional — more information is better than less during live trading.

### What It Cannot Do
- It cannot predict which day will be continuation vs failure before the session starts
- It cannot detect fundamental catalysts, news events, or sector rotation
- It does not factor in options flow, level 2, or order book data
- It does not adjust for earnings days, FOMC, or other macro events
- The contrary candle state engine requires FT to fire before any state labels show — pre-FT, only the raw signal probability (68%/67%) is displayed

---

## Appendix: Version History

| Version | Key Changes |
|---|---|
| v4.5 | Enhanced gap bias with confidence tiers, slope magnitude, prior-bar TrendScore zone context |
| v5.0 | Added contrary candle FT tracking (fade/bounce paths), E3 windows, pullback/adverse zones |
| v5.1 | HoD/LoD bar tracking, state engines (fadeState/bounceState) replacing static time phases for contrary candles, combined filter stacks from deep dive data |
| v5.1+ | Divergence guard system (symmetric for all 4 paths), ENTRY @ price labels for all paths, divergence label updated to pink "Divergence — Mean reversion possible" |
| v6.0 | 5-tier opening candle classification (MAX_BULL/BULL/NEUTRAL/BEAR/MAX_BEAR), regime-specific WRs from 11,733-event study, Reverse FT detection with TS level qualification, State 11 (REVERSED) added to state engine, fixed divergence logic (histogram color vs candle) |
| v6.1 | **Bearish Parity:** Per-bucket shortLoDBar (was flat bar48/66), per-bucket MAE thresholds for all 3 bearish paths (short continuation, fade, bounce), V-bottom early warning system (87% rate at LoD <30m), median destination time labels, enhanced E3 short label ("85% BOUNCE ABOVE ENTRY"), state 2 labels show per-bucket expected MAE |
